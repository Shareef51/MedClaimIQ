from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RAGChunkModel(TimestampMixin, Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "chunk_fingerprint", name="rag_chunk_fingerprint_per_tenant"),
        Index("ix_rag_chunk_claim_domain", "tenant_id", "claim_id", "domain", "source_id"),
        Index("ix_rag_chunk_source_version", "tenant_id", "source_type", "source_id", "source_version"),
        Index("ix_rag_chunk_parent", "tenant_id", "parent_chunk_id"),
    )

    chunk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    parent_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("rag_chunks.chunk_id", ondelete="CASCADE"), nullable=True, index=True)
    chunk_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    citation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    payload_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class RAGIndexJobModel(TimestampMixin, Base):
    __tablename__ = "rag_index_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="rag_index_job_idempotency_per_tenant"),
        Index("ix_rag_index_job_claim_status", "tenant_id", "claim_id", "status"),
        Index("ix_rag_index_job_source", "tenant_id", "source_type", "source_id", "source_version"),
    )

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RAGIndexRecordModel(TimestampMixin, Base):
    __tablename__ = "rag_index_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "chunk_id", "embedding_model", "embedding_dimensions", "index_version", name="rag_chunk_embedding_projection_once"),
        Index("ix_rag_index_record_claim", "tenant_id", "claim_id", "domain", "active"),
        Index("ix_rag_index_record_source", "tenant_id", "source_id", "source_version", "active"),
    )

    index_record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("rag_chunks.chunk_id", ondelete="CASCADE"), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    collection_name: Mapped[str] = mapped_column(String(160), nullable=False)
    point_id: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RAGIndexDeadLetterModel(TimestampMixin, Base):
    __tablename__ = "rag_index_dead_letters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_id", name="one_rag_dead_letter_per_job"),
        Index("ix_rag_index_dlq_claim", "tenant_id", "claim_id", "created_at"),
    )

    dead_letter_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("rag_index_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_detail: Mapped[str] = mapped_column(Text, nullable=False)
    replay_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class RAGRetrievalRunModel(TimestampMixin, Base):
    __tablename__ = "rag_retrieval_runs"
    __table_args__ = (
        Index("ix_rag_retrieval_run_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_rag_retrieval_run_query_hash", "tenant_id", "query_sha256"),
    )

    retrieval_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_length: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    planned_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    query_variant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    source_diversity: Mapped[float] = mapped_column(Float, nullable=False)
    no_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    no_evidence_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    fallback_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    planner_version: Mapped[str] = mapped_column(String(120), nullable=False)
    reranker_version: Mapped[str] = mapped_column(String(120), nullable=False)
    compression_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RAGRetrievalCandidateModel(Base):
    __tablename__ = "rag_retrieval_candidates"
    __table_args__ = (
        Index("ix_rag_retrieval_candidate_run", "tenant_id", "retrieval_run_id", "final_rank"),
        Index("ix_rag_retrieval_candidate_chunk", "tenant_id", "chunk_id"),
    )

    candidate_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    retrieval_run_id: Mapped[str] = mapped_column(ForeignKey("rag_retrieval_runs.retrieval_run_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    final_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    dense_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sparse_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fused_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retrieval_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
