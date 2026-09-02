from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ClaimReserveSnapshotModel(Base):
    __tablename__ = "claim_reserve_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "source_watermark_sha256", name="uq_claim_reserve_watermark"),
        Index("ix_claim_reserve_claim_time", "tenant_id", "claim_id", "created_at"),
    )
    reserve_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    decision_history_sha256: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    incurred_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net_paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    outstanding_reserve: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    prior_outstanding_reserve: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reserve_variance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    adequacy_score: Mapped[int] = mapped_column(Integer, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class FinancialAnalyticsSnapshotModel(Base):
    __tablename__ = "financial_analytics_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scope_type", "scope_id", "source_watermark_sha256", name="uq_fin_analytics_scope_watermark"),
        Index("ix_fin_analytics_scope_time", "tenant_id", "scope_type", "scope_id", "created_at"),
    )
    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, default="portfolio")
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    anomalies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_actor_type: Mapped[str] = mapped_column(String(50), nullable=False, default="deterministic_read_only_analytics")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class FinancialAnomalyInvestigationModel(Base):
    __tablename__ = "financial_anomaly_investigations"
    __table_args__ = (Index("ix_fin_anomaly_claim_score", "tenant_id", "claim_id", "anomaly_score"),)
    investigation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"))
    anomaly_code: Mapped[str] = mapped_column(String(100), nullable=False)
    anomaly_score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    factors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    adjudication_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    accounting_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    fund_movement_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class FinancialCopilotRunModel(Base):
    __tablename__ = "financial_copilot_runs"
    __table_args__ = (Index("ix_fin_copilot_user_time", "tenant_id", "requested_by_user_id", "created_at"),)
    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retrieval_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    adjudication_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    accounting_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    fund_movement_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
