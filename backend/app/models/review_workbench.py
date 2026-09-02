from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class ReviewWorkItemModel(TimestampMixin, Base):
    __tablename__ = "review_work_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", name="uq_review_work_item_claim"),
        Index("ix_review_work_queue", "tenant_id", "status", "priority_score", "created_at"),
        Index("ix_review_work_assignee", "tenant_id", "assigned_reviewer_user_id", "status"),
    )
    work_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    priority_band: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    priority_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewClaimLockModel(Base):
    __tablename__ = "review_claim_locks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", name="uq_review_claim_lock"),
        Index("ix_review_lock_expiry", "tenant_id", "locked_until"),
    )
    lock_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="CASCADE"), nullable=False, index=True)
    lock_token_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewerNoteModel(Base):
    __tablename__ = "reviewer_notes"
    __table_args__ = (Index("ix_reviewer_note_claim", "tenant_id", "claim_id", "created_at"),)
    note_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(30), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewActionEventModel(Base):
    __tablename__ = "review_action_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_review_action_idempotency"),
        Index("ix_review_action_claim", "tenant_id", "claim_id", "sequence"),
    )
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewDecisionMetadataModel(Base):
    __tablename__ = "review_decision_metadata"
    __table_args__ = (Index("ix_review_decision_meta_claim", "tenant_id", "claim_id", "created_at"),)
    metadata_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="CASCADE"), nullable=False, unique=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ai_recommendation: Mapped[str | None] = mapped_column(String(80), nullable=True)
    override_ai_recommendation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_claim_status_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
