from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.rag import RAGChunk
from app.models.knowledge_governance import KnowledgeDocumentVersionModel
from app.models.rag import (
    RAGChunkModel, RAGIndexDeadLetterModel, RAGIndexJobModel, RAGIndexRecordModel,
    RAGRetrievalCandidateModel, RAGRetrievalRunModel,
)


class RAGRepository:
    def __init__(self, session: Session, *, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def save_chunks(self, chunks: Sequence[RAGChunk]) -> list[RAGChunkModel]:
        records: list[RAGChunkModel] = []
        for chunk in chunks:
            if chunk.tenant_id != self.tenant_id:
                raise PermissionError("cross-tenant RAG chunk write denied")
            existing = self.session.get(RAGChunkModel, chunk.chunk_id)
            if existing is not None:
                records.append(existing)
                continue
            record = RAGChunkModel(
                chunk_id=chunk.chunk_id,
                tenant_id=chunk.tenant_id,
                claim_id=chunk.claim_id,
                patient_subject_id=chunk.patient_subject_id,
                domain=chunk.domain.value,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                source_version=chunk.source_version,
                parent_chunk_id=chunk.parent_chunk_id,
                chunk_kind=chunk.kind.value,
                ordinal=chunk.ordinal,
                content_text=chunk.text,
                content_sha256=chunk.content_sha256,
                chunk_fingerprint=chunk.content_sha256 + ":" + chunk.chunk_id[-16:],
                token_count=chunk.token_count,
                citation=chunk.citation,
                payload_metadata=chunk.metadata,
                active=True,
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def deactivate_other_source_versions(self, *, source_type: str, source_id: str, keep_version: str) -> None:
        self.session.execute(
            update(RAGChunkModel)
            .where(
                RAGChunkModel.tenant_id == self.tenant_id,
                RAGChunkModel.source_type == source_type,
                RAGChunkModel.source_id == source_id,
                RAGChunkModel.source_version != keep_version,
            )
            .values(active=False)
        )
        self.session.execute(
            update(RAGIndexRecordModel)
            .where(
                RAGIndexRecordModel.tenant_id == self.tenant_id,
                RAGIndexRecordModel.source_id == source_id,
                RAGIndexRecordModel.source_version != keep_version,
            )
            .values(active=False)
        )


    def deactivate_stale_index_versions(self, *, source_id: str, source_version: str, keep_index_version: str) -> None:
        self.session.execute(
            update(RAGIndexRecordModel)
            .where(
                RAGIndexRecordModel.tenant_id == self.tenant_id,
                RAGIndexRecordModel.source_id == source_id,
                (RAGIndexRecordModel.source_version != source_version) | (RAGIndexRecordModel.index_version != keep_index_version),
            )
            .values(active=False)
        )

    def deactivate_stale_projection_configs(self, *, source_id: str, source_version: str,
                                            keep_embedding_model: str, keep_embedding_dimensions: int,
                                            keep_index_version: str) -> None:
        self.session.execute(
            update(RAGIndexRecordModel)
            .where(
                RAGIndexRecordModel.tenant_id == self.tenant_id,
                RAGIndexRecordModel.source_id == source_id,
                RAGIndexRecordModel.source_version == source_version,
                (
                    (RAGIndexRecordModel.embedding_model != keep_embedding_model)
                    | (RAGIndexRecordModel.embedding_dimensions != keep_embedding_dimensions)
                    | (RAGIndexRecordModel.index_version != keep_index_version)
                ),
            )
            .values(active=False)
        )

    def deactivate_source(self, *, source_id: str, source_version: str | None = None) -> None:
        conditions = [RAGChunkModel.tenant_id == self.tenant_id, RAGChunkModel.source_id == source_id]
        index_conditions = [RAGIndexRecordModel.tenant_id == self.tenant_id, RAGIndexRecordModel.source_id == source_id]
        if source_version is not None:
            conditions.append(RAGChunkModel.source_version == source_version)
            index_conditions.append(RAGIndexRecordModel.source_version == source_version)
        self.session.execute(update(RAGChunkModel).where(*conditions).values(active=False))
        self.session.execute(update(RAGIndexRecordModel).where(*index_conditions).values(active=False))

    def parent_chunks(self, chunk_ids: Iterable[str]) -> dict[str, RAGChunkModel]:
        ids = sorted(set(chunk_ids))
        if not ids:
            return {}
        rows = self.session.scalars(
            select(RAGChunkModel).where(RAGChunkModel.tenant_id == self.tenant_id, RAGChunkModel.chunk_id.in_(ids))
        ).all()
        return {row.chunk_id: row for row in rows}

    def add_index_records(self, records: Sequence[RAGIndexRecordModel]) -> None:
        for record in records:
            if record.tenant_id != self.tenant_id:
                raise PermissionError("cross-tenant RAG index record write denied")
            self.session.add(record)
        self.session.flush()

    def create_job(self, job: RAGIndexJobModel) -> RAGIndexJobModel:
        if job.tenant_id != self.tenant_id:
            raise PermissionError("cross-tenant RAG job write denied")
        existing = self.session.scalar(
            select(RAGIndexJobModel).where(
                RAGIndexJobModel.tenant_id == self.tenant_id,
                RAGIndexJobModel.idempotency_key == job.idempotency_key,
            )
        )
        if existing:
            return existing
        self.session.add(job)
        self.session.flush()
        return job

    def add_dead_letter(self, dead_letter: RAGIndexDeadLetterModel) -> None:
        if dead_letter.tenant_id != self.tenant_id:
            raise PermissionError("cross-tenant RAG dead-letter write denied")
        self.session.add(dead_letter)
        self.session.flush()


    def filter_governed_retrieval_hits(self, hits, *, at=None):
        """Drop retired/future/expired governed knowledge while leaving legacy claim evidence unchanged."""
        if not hits:
            return []
        from datetime import UTC, datetime
        now = at or datetime.now(UTC)
        pairs = {(str(h.metadata.get("source_id", "")), str(h.metadata.get("source_version", ""))) for h in hits}
        source_ids = sorted({source_id for source_id, _ in pairs if source_id})
        if not source_ids:
            return list(hits)
        rows = list(self.session.scalars(select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.tenant_id == self.tenant_id,
            KnowledgeDocumentVersionModel.rag_source_id.in_(source_ids),
        )))
        governed = {}
        for row in rows:
            key = (row.rag_source_id, row.rag_source_version)
            eligible = row.status == "active" and (row.valid_from is None or row.valid_from <= now) and (row.valid_to is None or row.valid_to > now)
            governed[key] = governed.get(key, False) or eligible
        filtered = []
        for hit in hits:
            key = (str(hit.metadata.get("source_id", "")), str(hit.metadata.get("source_version", "")))
            if key not in governed or governed[key]:
                filtered.append(hit)
        return filtered

    def add_retrieval_telemetry(
        self,
        run: RAGRetrievalRunModel,
        candidates: Sequence[RAGRetrievalCandidateModel],
    ) -> None:
        if run.tenant_id != self.tenant_id:
            raise PermissionError("cross-tenant RAG retrieval telemetry write denied")
        self.session.add(run)
        for candidate in candidates:
            if candidate.tenant_id != self.tenant_id or candidate.retrieval_run_id != run.retrieval_run_id:
                raise PermissionError("cross-tenant RAG candidate telemetry write denied")
            self.session.add(candidate)
        self.session.flush()
