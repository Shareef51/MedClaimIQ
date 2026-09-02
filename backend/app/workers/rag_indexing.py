from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.domain.rag import IndexAction, IndexJobStatus, KnowledgeDocument, RAGDomain
from app.models.rag import RAGIndexDeadLetterModel, RAGIndexJobModel
from app.repositories.rag import RAGRepository
from app.services.rag import RAGIndexingService, retry_delay_seconds


@dataclass(frozen=True)
class RAGIndexRequest:
    tenant_id: str
    claim_id: str
    document: KnowledgeDocument
    action: IndexAction
    idempotency_key: str
    trace_id: str | None = None


class RAGIndexWorker:
    def __init__(self, *, repository: RAGRepository, indexing: RAGIndexingService, max_attempts: int = 3) -> None:
        self.repository = repository
        self.indexing = indexing
        self.max_attempts = max_attempts

    def process(self, request: RAGIndexRequest) -> RAGIndexJobModel:
        if request.tenant_id != self.repository.tenant_id or request.document.tenant_id != request.tenant_id:
            raise PermissionError("cross-tenant RAG indexing denied")
        now = datetime.now(UTC)
        job = self.repository.create_job(
            RAGIndexJobModel(
                job_id=f"ragjob_{uuid.uuid4().hex}",
                tenant_id=request.tenant_id,
                claim_id=request.claim_id,
                domain=request.document.domain.value,
                source_type=request.document.source_type,
                source_id=request.document.source_id,
                source_version=request.document.source_version,
                action=request.action.value,
                status=IndexJobStatus.PENDING.value,
                attempt_number=0,
                max_attempts=self.max_attempts,
                idempotency_key=request.idempotency_key,
                trace_id=request.trace_id,
            )
        )
        if job.status == IndexJobStatus.COMPLETED.value:
            return job
        job.attempt_number += 1
        job.status = IndexJobStatus.RUNNING.value
        job.started_at = now
        try:
            if request.action is IndexAction.DELETE:
                self.indexing.delete_source(
                    domain=request.document.domain,
                    tenant_id=request.tenant_id,
                    source_id=request.document.source_id,
                    source_version=request.document.source_version,
                )
            else:
                self.indexing.index_document(request.document, replace_previous_versions=request.action is IndexAction.REINDEX)
            job.status = IndexJobStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC)
            job.error_code = None
            job.error_detail = None
            return job
        except Exception as exc:
            job.error_code = type(exc).__name__
            job.error_detail = str(exc)[:4000]
            if job.attempt_number >= job.max_attempts:
                job.status = IndexJobStatus.DEAD_LETTER.value
                self.repository.add_dead_letter(
                    RAGIndexDeadLetterModel(
                        dead_letter_id=f"ragdlq_{uuid.uuid4().hex}",
                        tenant_id=request.tenant_id,
                        claim_id=request.claim_id,
                        job_id=job.job_id,
                        error_code=job.error_code,
                        error_detail=job.error_detail,
                        replay_payload={
                            "action": request.action.value,
                            "domain": request.document.domain.value,
                            "source_type": request.document.source_type,
                            "source_id": request.document.source_id,
                            "source_version": request.document.source_version,
                            "idempotency_key": request.idempotency_key,
                        },
                        trace_id=request.trace_id,
                    )
                )
            else:
                job.status = IndexJobStatus.RETRY.value
                job.next_attempt_at = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds(attempt=job.attempt_number))
            return job
