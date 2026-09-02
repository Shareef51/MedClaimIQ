from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ReviewDecisionPacketModel(Base):
    __tablename__ = "review_decision_packets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_review_decision_packet_idempotency"),
        Index("ix_review_decision_packet_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_review_decision_packet_status", "tenant_id", "status", "updated_at"),
    )
    packet_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    primary_reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    second_reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    denied_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    partial_line_decisions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_snapshot: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    annotation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    inconsistency_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    checkpoint_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ai_recommendation: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_disagreement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_disagreement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completeness: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    blocker_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    escalation_queue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dual_control_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    packet_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expected_claim_status_version: Mapped[int] = mapped_column(Integer, nullable=False)
    locked_payload_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="RESTRICT"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DecisionSecondReviewModel(Base):
    __tablename__ = "decision_second_reviews"
    __table_args__ = (
        UniqueConstraint("tenant_id", "packet_id", "reviewer_user_id", name="uq_second_review_packet_reviewer"),
        Index("ix_second_review_packet", "tenant_id", "packet_id", "created_at"),
    )
    second_review_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id: Mapped[str] = mapped_column(ForeignKey("review_decision_packets.packet_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    packet_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdjudicationAuditEventModel(Base):
    __tablename__ = "adjudication_audit_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "sequence", name="uq_adjudication_audit_sequence"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_adjudication_audit_idempotency"),
        Index("ix_adjudication_audit_claim", "tenant_id", "claim_id", "sequence"),
    )
    audit_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id: Mapped[str | None] = mapped_column(ForeignKey("review_decision_packets.packet_id", ondelete="SET NULL"), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_event_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionNotificationIntentModel(Base):
    __tablename__ = "decision_notification_intents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_decision_notification_idempotency"),
        Index("ix_decision_notification_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_decision_notification_status", "tenant_id", "status", "created_at"),
    )
    notification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id: Mapped[str] = mapped_column(ForeignKey("review_decision_packets.packet_id", ondelete="CASCADE"), nullable=False)
    audience: Mapped[str] = mapped_column(String(60), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_delivery")
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
