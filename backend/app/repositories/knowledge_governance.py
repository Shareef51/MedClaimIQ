from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.models.knowledge_governance import (
    KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeGovernanceEventModel,
    KnowledgeIndexMigrationModel, KnowledgeQualityRunModel, KnowledgeReindexJobModel,
    KnowledgeReleaseItemModel, KnowledgeReleaseModel, KnowledgeRetrievalDriftModel, KnowledgeSourceModel,
)
from app.models.rag import RAGChunkModel, RAGIndexRecordModel


class KnowledgeGovernanceRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def add(self, model):
        if getattr(model, "tenant_id", self.tenant_id) != self.tenant_id:
            raise PermissionError("cross-tenant knowledge governance write denied")
        self.session.add(model)
        self.session.flush()
        return model

    def source(self, source_id: str):
        return self.session.scalar(select(KnowledgeSourceModel).where(
            KnowledgeSourceModel.tenant_id == self.tenant_id, KnowledgeSourceModel.source_id == source_id))

    def document(self, document_id: str):
        return self.session.scalar(select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.tenant_id == self.tenant_id, KnowledgeDocumentModel.document_id == document_id))

    def version(self, version_id: str):
        return self.session.scalar(select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.tenant_id == self.tenant_id, KnowledgeDocumentVersionModel.version_id == version_id))

    def versions_for_document(self, document_id: str):
        return list(self.session.scalars(select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.tenant_id == self.tenant_id,
            KnowledgeDocumentVersionModel.document_id == document_id,
        ).order_by(KnowledgeDocumentVersionModel.created_at.desc())))

    def active_versions(self):
        return list(self.session.scalars(select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.tenant_id == self.tenant_id,
            KnowledgeDocumentVersionModel.status == "active",
        )))

    def latest_quality(self, version_id: str):
        return self.session.scalar(select(KnowledgeQualityRunModel).where(
            KnowledgeQualityRunModel.tenant_id == self.tenant_id,
            KnowledgeQualityRunModel.version_id == version_id,
        ).order_by(KnowledgeQualityRunModel.created_at.desc()).limit(1))

    def latest_blocking_drift(self):
        return self.session.scalar(select(KnowledgeRetrievalDriftModel).where(
            KnowledgeRetrievalDriftModel.tenant_id == self.tenant_id,
            KnowledgeRetrievalDriftModel.blocking.is_(True),
        ).order_by(KnowledgeRetrievalDriftModel.created_at.desc()).limit(1))

    def release(self, release_id: str):
        return self.session.scalar(select(KnowledgeReleaseModel).where(
            KnowledgeReleaseModel.tenant_id == self.tenant_id, KnowledgeReleaseModel.release_id == release_id))

    def release_items(self, release_id: str):
        return list(self.session.scalars(select(KnowledgeReleaseItemModel).where(
            KnowledgeReleaseItemModel.tenant_id == self.tenant_id,
            KnowledgeReleaseItemModel.release_id == release_id,
        )))

    def retire_other_versions(self, document_id: str, keep_version_id: str, retired_at) -> list[str]:
        rows = list(self.session.scalars(select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.tenant_id == self.tenant_id,
            KnowledgeDocumentVersionModel.document_id == document_id,
            KnowledgeDocumentVersionModel.version_id != keep_version_id,
            KnowledgeDocumentVersionModel.status == "active",
        )))
        for row in rows:
            row.status = "retired"
            row.retired_at = retired_at
        self.session.flush()
        return [row.version_id for row in rows]

    def chunks_for_version(self, version) -> list[RAGChunkModel]:
        return list(self.session.scalars(select(RAGChunkModel).where(
            RAGChunkModel.tenant_id == self.tenant_id,
            RAGChunkModel.source_id == version.rag_source_id,
            RAGChunkModel.source_version == version.rag_source_version,
            RAGChunkModel.active.is_(True),
        )))

    def current_projection_records(self, version, *, embedding_model: str, embedding_dimensions: int,
                                   index_version: str, active_only: bool = True):
        conditions = [
            RAGIndexRecordModel.tenant_id == self.tenant_id,
            RAGIndexRecordModel.source_id == version.rag_source_id,
            RAGIndexRecordModel.source_version == version.rag_source_version,
            RAGIndexRecordModel.embedding_model == embedding_model,
            RAGIndexRecordModel.embedding_dimensions == embedding_dimensions,
            RAGIndexRecordModel.index_version == index_version,
        ]
        if active_only:
            conditions.append(RAGIndexRecordModel.active.is_(True))
        return list(self.session.scalars(select(RAGIndexRecordModel).where(*conditions)))

    def stale_chunk_ids(self, version, *, embedding_model: str, embedding_dimensions: int, index_version: str) -> list[str]:
        chunks = [c for c in self.chunks_for_version(version) if c.chunk_kind != "parent"]
        if not chunks:
            return ["__missing_source_chunks__"]
        records = {r.chunk_id: r for r in self.current_projection_records(
            version, embedding_model=embedding_model, embedding_dimensions=embedding_dimensions, index_version=index_version)}
        stale = []
        for chunk in chunks:
            record = records.get(chunk.chunk_id)
            if record is None or record.embedding_input_sha256 != chunk.content_sha256:
                stale.append(chunk.chunk_id)
        return stale

    def index_migration(self, migration_id: str):
        return self.session.scalar(select(KnowledgeIndexMigrationModel).where(
            KnowledgeIndexMigrationModel.tenant_id == self.tenant_id,
            KnowledgeIndexMigrationModel.migration_id == migration_id,
        ))

    def migration_jobs(self, migration_id: str):
        return list(self.session.scalars(select(KnowledgeReindexJobModel).where(
            KnowledgeReindexJobModel.tenant_id == self.tenant_id,
            KnowledgeReindexJobModel.migration_id == migration_id,
        )))

    def reindex_job_by_key(self, idempotency_key: str):
        return self.session.scalar(select(KnowledgeReindexJobModel).where(
            KnowledgeReindexJobModel.tenant_id == self.tenant_id,
            KnowledgeReindexJobModel.idempotency_key == idempotency_key,
        ))

    def pending_reindex_jobs(self, limit: int = 50):
        return list(self.session.scalars(select(KnowledgeReindexJobModel).where(
            KnowledgeReindexJobModel.tenant_id == self.tenant_id,
            KnowledgeReindexJobModel.status.in_(["pending", "retry"]),
        ).order_by(KnowledgeReindexJobModel.created_at.asc()).limit(limit)))

    def sources(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeSourceModel).where(
            KnowledgeSourceModel.tenant_id == self.tenant_id).order_by(KnowledgeSourceModel.created_at.desc()).limit(limit)))

    def documents(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.tenant_id == self.tenant_id).order_by(KnowledgeDocumentModel.created_at.desc()).limit(limit)))

    def releases(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeReleaseModel).where(
            KnowledgeReleaseModel.tenant_id == self.tenant_id).order_by(KnowledgeReleaseModel.created_at.desc()).limit(limit)))

    def quality_runs(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeQualityRunModel).where(
            KnowledgeQualityRunModel.tenant_id == self.tenant_id).order_by(KnowledgeQualityRunModel.created_at.desc()).limit(limit)))

    def drift_events(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeRetrievalDriftModel).where(
            KnowledgeRetrievalDriftModel.tenant_id == self.tenant_id).order_by(KnowledgeRetrievalDriftModel.created_at.desc()).limit(limit)))

    def events(self, limit: int = 100):
        return list(self.session.scalars(select(KnowledgeGovernanceEventModel).where(
            KnowledgeGovernanceEventModel.tenant_id == self.tenant_id).order_by(KnowledgeGovernanceEventModel.created_at.desc()).limit(limit)))
