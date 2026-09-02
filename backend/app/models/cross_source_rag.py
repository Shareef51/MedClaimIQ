from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EvidencePackModel(TimestampMixin, Base):
    __tablename__ = "rag_evidence_packs"
    __table_args__ = (
        Index("ix_rag_evidence_pack_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_rag_evidence_pack_query", "tenant_id", "query_sha256"),
        CheckConstraint("query_length >= 0 AND evidence_count >= 0 AND contradiction_count >= 0", name="evidence_pack_nonnegative"),
        CheckConstraint("confidence >= 0 AND confidence <= 1 AND coverage >= 0 AND coverage <= 1 AND source_diversity >= 0 AND source_diversity <= 1", name="evidence_pack_score_range"),
    )
    pack_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_length: Mapped[int] = mapped_column(Integer, nullable=False)
    planner_version: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_retrievers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    executed_retrievers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    source_diversity: Mapped[float] = mapped_column(Float, nullable=False)
    no_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unresolved_material_contradictions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assessment_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class EvidencePackItemModel(Base):
    __tablename__ = "rag_evidence_pack_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pack_id", "evidence_key", name="evidence_once_per_pack"),
        Index("ix_rag_evidence_pack_item_pack", "tenant_id", "pack_id", "rank"),
        CheckConstraint("rank >= 1 AND authority_rank >= 0 AND authority_rank <= 100 AND confidence >= 0 AND confidence <= 1", name="evidence_pack_item_range"),
    )
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_key: Mapped[str] = mapped_column(String(128), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    retriever: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    citation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidencePackContradictionModel(Base):
    __tablename__ = "rag_evidence_pack_contradictions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pack_id", "contradiction_id", name="contradiction_once_per_pack"),
        Index("ix_rag_evidence_pack_contradiction", "tenant_id", "pack_id", "severity"),
    )
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    contradiction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
