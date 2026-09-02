from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class PortalDocumentRequestModel(TimestampMixin, Base):
    __tablename__ = "portal_document_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_decision_id", name="uq_portal_request_source_decision"),
        Index("ix_portal_request_claim", "tenant_id", "claim_id", "status", "created_at"),
    )
    request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    source_decision_id: Mapped[str | None] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="SET NULL"), nullable=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    requested_document_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satisfied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortalSubmissionModel(TimestampMixin, Base):
    __tablename__ = "portal_submissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "upload_session_id", name="uq_portal_submission_upload"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_portal_submission_idempotency"),
        Index("ix_portal_submission_claim", "tenant_id", "claim_id", "created_at"),
    )
    submission_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("portal_document_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    upload_session_id: Mapped[str] = mapped_column(ForeignKey("evidence_upload_sessions.upload_session_id", ondelete="RESTRICT"), nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="SET NULL"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="upload_pending")
    acknowledgement_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortalActionEventModel(Base):
    __tablename__ = "portal_action_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_portal_action_idempotency"),
        Index("ix_portal_action_claim", "tenant_id", "claim_id", "occurred_at"),
    )
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
