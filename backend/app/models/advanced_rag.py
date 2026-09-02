from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AdvancedRAGRunModel(TimestampMixin, Base):
    __tablename__ = "advanced_rag_runs"
    __table_args__ = (
        Index("ix_advanced_rag_run_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_advanced_rag_run_trace", "tenant_id", "trace_id"),
        Index("ix_advanced_rag_run_query", "tenant_id", "query_sha256"),
    )

    advanced_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    retrieval_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_length: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(80))
    query_intent: Mapped[str] = mapped_column(String(50), nullable=False)
    routing_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    retrieval_strategy: Mapped[str] = mapped_column(String(30), nullable=False)
    planner_version: Mapped[str] = mapped_column(String(120), nullable=False)
    reranker_version: Mapped[str] = mapped_column(String(120), nullable=False)
    rewrite_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hyde_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_assisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    planned_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_predicates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    citation_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    answerability: Mapped[str] = mapped_column(String(30), nullable=False)
    knowledge_gap_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds_executed: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128))


class AdvancedRAGEventModel(Base):
    __tablename__ = "advanced_rag_events"
    __table_args__ = (
        Index("ix_advanced_rag_event_run", "tenant_id", "advanced_run_id", "created_at"),
    )

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    advanced_run_id: Mapped[str] = mapped_column(ForeignKey("advanced_rag_runs.advanced_run_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
