from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Sequence

from app.domain.rag import QueryPlan, RetrievalAssessment, RetrievalHit, RetrievalStrategy
from app.models.rag import RAGRetrievalCandidateModel, RAGRetrievalRunModel
from app.repositories.rag import RAGRepository
from app.rag.reranking import EvidenceAwareReranker
from app.services.rag import RetrievalTelemetrySink
from app.observability.metrics import record_operation
from app.observability.tracing import traced_operation


class PostgresRetrievalTelemetry(RetrievalTelemetrySink):
    """Persist retrieval telemetry without storing raw medical queries by default."""

    def __init__(self, repository: RAGRepository) -> None:
        self.repository = repository

    def record(
        self,
        *,
        run_id: str,
        query: str,
        plan: QueryPlan,
        strategy: RetrievalStrategy,
        candidates: Sequence[RetrievalHit],
        selected: Sequence[RetrievalHit],
        assessment: RetrievalAssessment,
        fallback_steps: Sequence[str],
        latency_ms: int,
        compression_applied: bool,
        trace_id: str | None,
    ) -> None:
        tenant_id = self.repository.tenant_id
        claim_id = str(selected[0].metadata.get("claim_id")) if selected else ""
        if not claim_id:
            # Candidate metadata remains security-scoped and contains claim_id from indexing.
            claim_id = str(candidates[0].metadata.get("claim_id")) if candidates else ""
        if not claim_id:
            return
        run = RAGRetrievalRunModel(
            retrieval_run_id=run_id,
            tenant_id=tenant_id,
            claim_id=claim_id,
            query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
            query_length=len(query),
            strategy=strategy.value,
            requested_domains=[item.value for item in plan.domains],
            planned_domains=[item.value for item in plan.domains],
            query_variant_count=len(plan.variants),
            candidate_count=len(candidates),
            selected_count=len(selected),
            confidence=assessment.confidence,
            coverage=assessment.coverage,
            source_diversity=assessment.source_diversity,
            no_evidence=assessment.no_evidence,
            no_evidence_reasons=list(assessment.reasons),
            fallback_steps=list(fallback_steps),
            latency_ms=latency_ms,
            trace_id=trace_id,
            planner_version=plan.planner_version,
            reranker_version=EvidenceAwareReranker.version,
            compression_applied=compression_applied,
        )
        selected_ids = {item.chunk_id for item in selected}
        events: list[RAGRetrievalCandidateModel] = []
        now = datetime.now(UTC)
        for rank, hit in enumerate(candidates, start=1):
            events.append(
                RAGRetrievalCandidateModel(
                    candidate_event_id=f"ragcand_{uuid.uuid4().hex}",
                    tenant_id=tenant_id,
                    claim_id=claim_id,
                    retrieval_run_id=run_id,
                    chunk_id=hit.chunk_id,
                    domain=hit.domain.value,
                    source_id=str(hit.metadata.get("source_id")) if hit.metadata.get("source_id") else None,
                    final_rank=rank,
                    dense_score=hit.dense_score,
                    sparse_score=hit.sparse_score,
                    fused_score=hit.fused_score,
                    rerank_score=hit.rerank_score,
                    selected=hit.chunk_id in selected_ids,
                    retrieval_sources=list(hit.retrieval_sources),
                    metadata_summary={
                        "authority_rank": hit.metadata.get("authority_rank"),
                        "evidence_confidence": hit.metadata.get("evidence_confidence"),
                        "source_type": hit.metadata.get("source_type"),
                        "source_version": hit.metadata.get("source_version"),
                    },
                    created_at=now,
                )
            )
        self.repository.add_retrieval_telemetry(run, events)
        record_operation(operation="rag.retrieval",latency_ms=latency_ms,status="no_evidence" if assessment.no_evidence else "success",attributes={"strategy":strategy.value,"selected_count":len(selected)})
