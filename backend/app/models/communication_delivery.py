from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CommunicationEndpointModel(Base):
    __tablename__ = "communication_endpoints"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "audience", "channel", name="uq_comm_endpoint_claim_audience_channel"),
        Index("ix_comm_endpoint_claim", "tenant_id", "claim_id", "audience"),
    )
    endpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    audience: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    destination_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    destination_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    encryption_key_version: Mapped[str] = mapped_column(String(40), nullable=False)
    consent_status: Mapped[str] = mapped_column(String(30), nullable=False)
    locale: Mapped[str] = mapped_column(String(12), nullable=False, default="en")
    accessibility_preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    endpoint_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by_actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationTemplateModel(Base):
    __tablename__ = "communication_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "template_key", "template_version", "locale", "channel", name="uq_comm_template_version"),
        Index("ix_comm_template_lookup", "tenant_id", "template_key", "locale", "channel", "status"),
    )
    template_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    template_version: Mapped[str] = mapped_column(String(40), nullable=False)
    locale: Mapped[str] = mapped_column(String(12), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    accessibility_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommunicationDispatchModel(Base):
    __tablename__ = "communication_dispatches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_comm_dispatch_idempotency"),
        Index("ix_comm_dispatch_worker", "tenant_id", "status", "next_attempt_at", "lease_until"),
        Index("ix_comm_dispatch_claim", "tenant_id", "claim_id", "created_at"),
    )
    dispatch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    notice_id: Mapped[str] = mapped_column(ForeignKey("decision_notices.notice_id", ondelete="CASCADE"), nullable=False)
    notification_id: Mapped[str] = mapped_column(ForeignKey("decision_notification_intents.notification_id", ondelete="CASCADE"), nullable=False)
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("communication_endpoints.endpoint_id", ondelete="RESTRICT"), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("communication_templates.template_id", ondelete="RESTRICT"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(60), nullable=False)
    locale: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    rendered_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    rendered_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    regulatory_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommunicationReceiptModel(Base):
    __tablename__ = "communication_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_name", "provider_event_id", name="uq_comm_receipt_provider_event"),
        Index("ix_comm_receipt_dispatch", "tenant_id", "dispatch_id", "occurred_at"),
    )
    receipt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("communication_dispatches.dispatch_id", ondelete="CASCADE"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(60), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationReconciliationModel(Base):
    __tablename__ = "communication_reconciliations"
    __table_args__ = (Index("ix_comm_recon_claim", "tenant_id", "claim_id", "created_at"),)
    reconciliation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    notice_id: Mapped[str] = mapped_column(ForeignKey("decision_notices.notice_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_dispatches: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_dispatches: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_dispatches: Mapped[int] = mapped_column(Integer, nullable=False)
    gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reconciliation_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationLegalHoldModel(Base):
    __tablename__ = "communication_legal_holds"
    __table_args__ = (Index("ix_comm_hold_claim", "tenant_id", "claim_id", "released_at"),)
    hold_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    placed_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class CommunicationIncidentModel(Base):
    __tablename__ = "communication_incidents"
    __table_args__ = (Index("ix_comm_incident_status", "tenant_id", "status", "created_at"),)
    incident_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="SET NULL"), nullable=True)
    dispatch_id: Mapped[str | None] = mapped_column(ForeignKey("communication_dispatches.dispatch_id", ondelete="SET NULL"), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
