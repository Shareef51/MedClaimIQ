from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SLAPolicyModel(TimestampMixin, Base):
    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_key", "version", name="uq_sla_policy_version"),
        Index("ix_sla_policy_active", "tenant_id", "is_active", "effective_from"),
    )
    policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    policy_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    calendar_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    rules: Mapped[list] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True)


class SLAHolidayModel(Base):
    __tablename__ = "sla_calendar_holidays"
    __table_args__ = (
        UniqueConstraint("tenant_id", "calendar_key", "holiday_date", name="uq_sla_calendar_holiday"),
        Index("ix_sla_holiday_calendar", "tenant_id", "calendar_key", "holiday_date"),
    )
    holiday_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_key: Mapped[str] = mapped_column(String(120), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SLATimerModel(TimestampMixin, Base):
    __tablename__ = "sla_timers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_sla_timer_idempotency"),
        Index("ix_sla_timer_due", "tenant_id", "status", "next_action_at"),
        Index("ix_sla_timer_claim", "tenant_id", "claim_id", "status", "due_at"),
        Index("ix_sla_timer_type", "tenant_id", "timer_type", "status"),
    )
    timer_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("sla_policies.policy_id", ondelete="RESTRICT"), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    timer_type: Mapped[str] = mapped_column(String(80), nullable=False)
    clock_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    warning_schedule: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    next_warning_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_event_type: Mapped[str | None] = mapped_column(String(140), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class SLATimerEventModel(Base):
    __tablename__ = "sla_timer_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_sla_timer_event_idempotency"),
        Index("ix_sla_event_claim", "tenant_id", "claim_id", "occurred_at"),
        Index("ix_sla_event_timer", "tenant_id", "timer_id", "occurred_at"),
    )
    sla_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    timer_id: Mapped[str] = mapped_column(ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    timer_type: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SLAReviewQueueEntryModel(TimestampMixin, Base):
    __tablename__ = "sla_review_queue_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "timer_id", "escalation_level", name="uq_sla_review_queue_timer_level"),
        Index("ix_sla_review_queue", "tenant_id", "status", "priority", "created_at"),
        Index("ix_sla_review_claim", "tenant_id", "claim_id", "status"),
    )
    queue_entry_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    timer_id: Mapped[str] = mapped_column(ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_level: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    assigned_reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True)
    mcp_approval_id: Mapped[str | None] = mapped_column(ForeignKey("mcp_approval_requests.approval_id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_code: Mapped[str | None] = mapped_column(String(100), nullable=True)


class SLAWorkerFailureModel(Base):
    __tablename__ = "sla_worker_failures"
    __table_args__ = (
        UniqueConstraint("tenant_id", "timer_id", "attempt", name="uq_sla_worker_failure_attempt"),
        Index("ix_sla_worker_failure", "tenant_id", "created_at"),
    )
    failure_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    timer_id: Mapped[str] = mapped_column(ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
