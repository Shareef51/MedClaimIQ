from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EvidenceUploadSessionModel(TimestampMixin, Base):
    __tablename__ = "evidence_upload_sessions"
    __table_args__ = (
        CheckConstraint("expected_byte_size > 0", name="positive_expected_size"),
        CheckConstraint("actual_byte_size IS NULL OR actual_byte_size > 0", name="positive_actual_size"),
        UniqueConstraint("tenant_id", "idempotency_key", name="idempotency_per_tenant"),
        Index("ix_upload_session_tenant_claim", "tenant_id", "claim_id"),
        Index("ix_upload_session_tenant_status", "tenant_id", "status"),
        Index("ix_upload_session_expires", "tenant_id", "upload_expires_at"),
    )

    upload_session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    initiated_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bucket_name: Mapped[str] = mapped_column(String(128), nullable=False)
    quarantine_object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    accepted_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    client_filename_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    client_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    declared_media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    detected_media_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    media_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_etag: Mapped[str | None] = mapped_column(String(160), nullable=True)
    storage_version_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    media_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="initiated")
    status_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rejection_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rejection_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_artifacts.evidence_id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    upload_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MalwareScanModel(Base):
    __tablename__ = "malware_scans"
    __table_args__ = (
        UniqueConstraint("tenant_id", "upload_session_id", "attempt_number", name="attempt_per_upload"),
        Index("ix_malware_scan_tenant_upload", "tenant_id", "upload_session_id"),
        Index("ix_malware_scan_tenant_verdict", "tenant_id", "verdict"),
    )

    scan_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    upload_session_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_upload_sessions.upload_session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scanner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scanner_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    signature_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceProcessingEventModel(Base):
    __tablename__ = "evidence_processing_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="idempotency_per_tenant"),
        Index("ix_evidence_event_tenant_aggregate", "tenant_id", "aggregate_id", "occurred_at"),
        Index("ix_evidence_event_tenant_type", "tenant_id", "event_type", "occurred_at"),
    )

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceEventOutboxModel(TimestampMixin, Base):
    __tablename__ = "evidence_event_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_id", name="one_outbox_row_per_event"),
        Index("ix_evidence_outbox_dispatch", "status", "available_at", "created_at"),
        Index("ix_evidence_outbox_tenant_status", "tenant_id", "status"),
    )

    outbox_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_processing_events.event_id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(160), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
