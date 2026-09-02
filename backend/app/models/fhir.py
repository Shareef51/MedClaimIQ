from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class FHIRConnectionModel(TimestampMixin, Base):
    __tablename__ = "fhir_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "connection_key", name="connection_key_per_tenant"),
        Index("ix_fhir_connection_tenant_status", "tenant_id", "status"),
    )
    connection_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    connection_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    fhir_version: Mapped[str] = mapped_column(String(32), nullable=False, default="4.0.1")
    auth_mode: Mapped[str] = mapped_column(String(60), nullable=False, default="smart_backend_services")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    rate_limit_per_second: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=10)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    config_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class FHIRResourceSnapshotModel(TimestampMixin, Base):
    __tablename__ = "fhir_resource_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "connection_id", "resource_type", "logical_id", "version_id", name="fhir_version_per_connection"),
        Index("ix_fhir_snapshot_tenant_resource", "tenant_id", "resource_type", "logical_id"),
        Index("ix_fhir_snapshot_tenant_claim", "tenant_id", "claim_id"),
        Index("ix_fhir_snapshot_tenant_patient", "tenant_id", "patient_subject_id"),
    )
    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("fhir_connections.connection_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="SET NULL"), nullable=True, index=True)
    patient_subject_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    logical_id: Mapped[str] = mapped_column(String(256), nullable=False)
    version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_resource: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    canonical_resource: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    authoritative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FHIRProvenanceModel(Base):
    __tablename__ = "fhir_provenance"
    __table_args__ = (
        Index("ix_fhir_provenance_tenant_snapshot", "tenant_id", "snapshot_id"),
    )
    provenance_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("fhir_resource_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(160), nullable=False)
    source_endpoint: Mapped[str] = mapped_column(String(1500), nullable=False)
    fetched_by: Mapped[str] = mapped_column(String(120), nullable=False, default="fhir_gateway")
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PatientIdentityMatchModel(TimestampMixin, Base):
    __tablename__ = "patient_identity_matches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "patient_subject_id", "connection_id", "fhir_patient_id", name="identity_candidate_per_source"),
        Index("ix_identity_match_tenant_patient", "tenant_id", "patient_subject_id", "status"),
    )
    match_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("fhir_connections.connection_id", ondelete="CASCADE"), nullable=False, index=True)
    fhir_patient_id: Mapped[str] = mapped_column(String(256), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HospitalCrossVerificationModel(TimestampMixin, Base):
    __tablename__ = "hospital_cross_verifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "snapshot_id", "verification_type", name="verification_per_snapshot"),
        Index("ix_hospital_verification_tenant_claim", "tenant_id", "claim_id", "status"),
    )
    verification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("fhir_resource_snapshots.snapshot_id", ondelete="RESTRICT"), nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    findings: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class HealthcareEventModel(Base):
    __tablename__ = "healthcare_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="healthcare_event_idempotency_per_tenant"),
        Index("ix_healthcare_event_tenant_claim", "tenant_id", "claim_id", "occurred_at"),
    )
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthcareEventOutboxModel(TimestampMixin, Base):
    __tablename__ = "healthcare_event_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", name="healthcare_outbox_event_once"),
        Index("ix_healthcare_outbox_unpublished", "published_at", "created_at"),
    )
    outbox_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("healthcare_events.event_id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(String(180), nullable=False, default="medclaimiq.healthcare.events.v1")
    partition_key: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
