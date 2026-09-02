from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MultimodalRAGRunModel(TimestampMixin, Base):
    __tablename__ = "multimodal_rag_runs"
    __table_args__ = (
        Index("ix_multimodal_rag_run_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_multimodal_rag_run_trace", "tenant_id", "trace_id"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_length: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    intent: Mapped[str] = mapped_column(String(60), nullable=False)
    requested_modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    routed_modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    modality_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    citation_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    source_diversity: Mapped[float] = mapped_column(Float, nullable=False)
    inconsistency_count: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_gap_count: Mapped[int] = mapped_column(Integer, nullable=False)
    answerability: Mapped[str] = mapped_column(String(30), nullable=False)
    planner_version: Mapped[str] = mapped_column(String(120), nullable=False)
    reranker_version: Mapped[str] = mapped_column(String(120), nullable=False)
    verifier_version: Mapped[str] = mapped_column(String(120), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class MultimodalEvidencePackModel(Base):
    __tablename__ = "multimodal_evidence_packs"
    __table_args__ = (Index("ix_multimodal_pack_claim", "tenant_id", "claim_id", "created_at"),)

    pack_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    modality_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    citation_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    answerability: Mapped[str] = mapped_column(String(30), nullable=False)
    pack_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MultimodalRAGItemModel(Base):
    __tablename__ = "multimodal_rag_items"
    __table_args__ = (
        Index("ix_multimodal_item_run", "tenant_id", "run_id", "rank"),
        Index("ix_multimodal_item_source", "tenant_id", "source_id", "source_version"),
    )

    item_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("multimodal_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(160), nullable=False)
    modality: Mapped[str] = mapped_column(String(30), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    authority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    citation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieval_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MultimodalInconsistencyModel(Base):
    __tablename__ = "multimodal_inconsistencies"
    __table_args__ = (Index("ix_multimodal_inconsistency_run", "tenant_id", "run_id", "created_at"),)

    inconsistency_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("multimodal_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    field: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    left_item_id: Mapped[str] = mapped_column(String(160), nullable=False)
    right_item_id: Mapped[str] = mapped_column(String(160), nullable=False)
    left_value_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    right_value_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
