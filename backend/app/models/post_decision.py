from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DecisionNoticeModel(Base):
    __tablename__ = "decision_notices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_decision_notice_idempotency"),
        Index("ix_decision_notice_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_decision_notice_status", "tenant_id", "status", "updated_at"),
    )
    notice_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id: Mapped[str] = mapped_column(ForeignKey("review_decision_packets.packet_id", ondelete="RESTRICT"), nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="RESTRICT"), nullable=False)
    appeal_id: Mapped[str | None] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="SET NULL", use_alter=True, name="fk_decision_notice_appeal"), nullable=True)
    resolution_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    template_version: Mapped[str] = mapped_column(String(40), nullable=False)
    notice_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    audience: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    reason_explanations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rendered_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rendered_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    locked_decision_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_by_actor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    generated_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    released_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppealCaseModel(Base):
    __tablename__ = "appeal_cases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_case_idempotency"),
        Index("ix_appeal_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_appeal_status_due", "tenant_id", "status", "appeal_due_at"),
    )
    appeal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    original_packet_id: Mapped[str] = mapped_column(ForeignKey("review_decision_packets.packet_id", ondelete="RESTRICT"), nullable=False)
    original_decision_id: Mapped[str] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="RESTRICT"), nullable=False)
    notice_id: Mapped[str] = mapped_column(ForeignKey("decision_notices.notice_id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    submitter_actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    submitter_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    grounds: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    late_filing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    appeal_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    appeal_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealSupplementalEvidenceModel(Base):
    __tablename__ = "appeal_supplemental_evidence"
    __table_args__ = (
        UniqueConstraint("tenant_id", "appeal_id", "evidence_id", name="uq_appeal_supplemental_evidence"),
        Index("ix_appeal_supplemental", "tenant_id", "appeal_id", "linked_at"),
    )
    link_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="RESTRICT"), nullable=False)
    evidence_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    linked_by_actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    linked_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealReviewAssignmentModel(Base):
    __tablename__ = "appeal_review_assignments"
    __table_args__ = (Index("ix_appeal_assignment", "tenant_id", "appeal_id", "assigned_at"),)
    assignment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    assigned_by_actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    independence_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assignment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealResolutionModel(Base):
    __tablename__ = "appeal_resolutions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_resolution_idempotency"),
        UniqueConstraint("tenant_id", "appeal_id", name="uq_appeal_resolution_once"),
    )
    resolution_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="RESTRICT"), nullable=False)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    controlling_decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    original_evidence_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    supplemental_evidence_snapshot: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    supplemental_evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionHistoryVersionModel(Base):
    __tablename__ = "decision_history_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "sequence", name="uq_decision_history_sequence"),
        UniqueConstraint("tenant_id", "source_type", "source_id", name="uq_decision_history_source"),
        Index("ix_decision_history_claim", "tenant_id", "claim_id", "sequence"),
    )
    history_version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    human_reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    evidence_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_version_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalCorrespondenceModel(Base):
    __tablename__ = "external_correspondence"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_external_correspondence_idempotency"),
        Index("ix_correspondence_claim", "tenant_id", "claim_id", "occurred_at"),
    )
    correspondence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str | None] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="SET NULL"), nullable=True)
    notice_id: Mapped[str | None] = mapped_column(ForeignKey("decision_notices.notice_id", ondelete="SET NULL"), nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    audience: Mapped[str] = mapped_column(String(60), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationDeliveryAttemptModel(Base):
    __tablename__ = "communication_delivery_attempts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "notification_id", "attempt_number", name="uq_delivery_attempt_number"),
        Index("ix_delivery_attempt_notification", "tenant_id", "notification_id", "attempt_number"),
    )
    attempt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    notification_id: Mapped[str] = mapped_column(ForeignKey("decision_notification_intents.notification_id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationDeadLetterModel(Base):
    __tablename__ = "communication_dead_letters"
    __table_args__ = (UniqueConstraint("tenant_id", "notification_id", name="uq_communication_dlq_notification"),)
    dead_letter_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    notification_id: Mapped[str] = mapped_column(ForeignKey("decision_notification_intents.notification_id", ondelete="CASCADE"), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    final_error_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PostDecisionTaskModel(Base):
    __tablename__ = "post_decision_tasks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_post_decision_task_idempotency"),
        Index("ix_post_decision_task_queue", "tenant_id", "status", "due_at", "priority"),
    )
    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str | None] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=True)
    notice_id: Mapped[str | None] = mapped_column(ForeignKey("decision_notices.notice_id", ondelete="CASCADE"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    assigned_reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
