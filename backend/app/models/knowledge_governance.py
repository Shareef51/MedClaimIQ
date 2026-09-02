from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class KnowledgeSourceModel(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_key", name="uq_knowledge_source_tenant_key"),
        Index("ix_knowledge_source_tenant_status", "tenant_id", "status"),
    )
    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    source_key: Mapped[str] = mapped_column(String(180), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_team: Mapped[str | None] = mapped_column(String(128))
    authority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    onboarding_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class KnowledgeDocumentModel(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_id", "document_key", name="uq_knowledge_document_source_key"),
        Index("ix_knowledge_document_source", "tenant_id", "source_id"),
    )
    document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    document_key: Mapped[str] = mapped_column(String(220), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(1000))
    lifecycle_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class KnowledgeDocumentVersionModel(TimestampMixin, Base):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "document_id", "version", name="uq_knowledge_document_version"),
        Index("ix_knowledge_version_document_status", "tenant_id", "document_id", "status"),
        Index("ix_knowledge_version_source_ref", "tenant_id", "rag_source_id", "rag_source_version"),
    )
    version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_locator: Mapped[str | None] = mapped_column(String(1000))
    rag_source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    rag_source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(128))
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeQualityRunModel(TimestampMixin, Base):
    __tablename__ = "knowledge_quality_runs"
    __table_args__ = (Index("ix_knowledge_quality_version", "tenant_id", "version_id", "created_at"),)
    quality_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_document_versions.version_id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    citation_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeReindexJobModel(TimestampMixin, Base):
    __tablename__ = "knowledge_reindex_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_knowledge_reindex_idempotency"),
        Index("ix_knowledge_reindex_status", "tenant_id", "status", "next_attempt_at"),
    )
    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_document_versions.version_id", ondelete="CASCADE"), nullable=False, index=True)
    migration_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    index_version: Mapped[str] = mapped_column(String(100), nullable=False)
    projection_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    stale_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_sha256: Mapped[str | None] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)


class KnowledgeIndexMigrationModel(TimestampMixin, Base):
    __tablename__ = "knowledge_index_migrations"
    __table_args__ = (Index("ix_knowledge_index_migration_tenant_status", "tenant_id", "status"),)
    migration_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    from_embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    from_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    from_index_version: Mapped[str] = mapped_column(String(100), nullable=False)
    to_embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    to_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    to_index_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeRetrievalDriftModel(TimestampMixin, Base):
    __tablename__ = "knowledge_retrieval_drift_events"
    __table_args__ = (Index("ix_knowledge_drift_tenant_created", "tenant_id", "created_at"),)
    drift_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_id: Mapped[str | None] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False)
    baseline_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    observed_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    deltas: Mapped[dict] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(128), nullable=False)


class KnowledgeReleaseModel(TimestampMixin, Base):
    __tablename__ = "knowledge_releases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "release_key", "release_version", name="uq_knowledge_release_version"),
        Index("ix_knowledge_release_tenant_status", "tenant_id", "status", "created_at"),
    )
    release_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_key: Mapped[str] = mapped_column(String(180), nullable=False)
    release_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approval_reason: Mapped[str | None] = mapped_column(String(1000))
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeReleaseItemModel(TimestampMixin, Base):
    __tablename__ = "knowledge_release_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "release_id", "version_id", name="uq_knowledge_release_item"),
        Index("ix_knowledge_release_item_release", "tenant_id", "release_id"),
    )
    release_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("knowledge_releases.release_id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_document_versions.version_id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeGovernanceEventModel(TimestampMixin, Base):
    __tablename__ = "knowledge_governance_events"
    __table_args__ = (Index("ix_knowledge_event_tenant_created", "tenant_id", "created_at"),)
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    details_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
