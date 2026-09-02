from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RegulatoryReconciliationCaseModel(Base):
    __tablename__ = "regulatory_reconciliation_cases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "transmission_id", name="uq_reg_recon_case_transmission"),
        Index("ix_reg_recon_case_status", "tenant_id", "status", "sla_deadline_at"),
    )
    case_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    transmission_id: Mapped[str] = mapped_column(ForeignKey("regulatory_transmissions.transmission_id", ondelete="RESTRICT"), nullable=False)
    package_id: Mapped[str] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="RESTRICT"), nullable=False)
    destination_id: Mapped[str] = mapped_column(ForeignKey("regulatory_destinations.destination_id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    opened_reason: Mapped[str] = mapped_column(String(120), nullable=False)
    acknowledgment_status: Mapped[str | None] = mapped_column(String(40))
    rejection_root_cause: Mapped[str | None] = mapped_column(String(80))
    rejection_root_cause_rationale: Mapped[str | None] = mapped_column(Text)
    amendment_effectiveness: Mapped[str | None] = mapped_column(String(40))
    amendment_effectiveness_rationale: Mapped[str | None] = mapped_column(Text)
    source_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    case_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prepared_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"))
    sla_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryDeliveryControlAttestationModel(Base):
    __tablename__ = "regulatory_delivery_control_attestations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", "attestation_version", name="uq_reg_delivery_attestation_version"),
        Index("ix_reg_delivery_attestation_case", "tenant_id", "case_id", "attestation_version"),
    )
    attestation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="CASCADE"), nullable=False)
    attestation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    controls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    material_blockers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_samples: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    control_effectiveness_pct: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    prepared_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryComplianceExceptionModel(Base):
    __tablename__ = "regulatory_compliance_exceptions"
    __table_args__ = (Index("ix_reg_compliance_exception_status", "tenant_id", "status", "material", "created_at"),)
    exception_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="CASCADE"), nullable=False)
    exception_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    material: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_rationale: Mapped[str | None] = mapped_column(Text)


class RegulatorySupervisoryCertificationModel(Base):
    __tablename__ = "regulatory_supervisory_certifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", "certification_sequence", name="uq_reg_supervisory_cert_sequence"),
        UniqueConstraint("tenant_id", "attestation_id", name="uq_reg_supervisory_cert_attestation"),
    )
    certification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="RESTRICT"), nullable=False)
    attestation_id: Mapped[str] = mapped_column(ForeignKey("regulatory_delivery_control_attestations.attestation_id", ondelete="RESTRICT"), nullable=False)
    certification_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    prepared_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    supervisor_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    conclusion: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_certification_sha256: Mapped[str | None] = mapped_column(String(64))
    certification_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatorySupervisorAnnotationModel(Base):
    __tablename__ = "regulatory_supervisor_annotations"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_reg_supervisor_annotation_idem"),)
    annotation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(60), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatorySupervisorCorrespondenceModel(Base):
    __tablename__ = "regulatory_supervisor_correspondence"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_reg_supervisor_corr_idem"),)
    correspondence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(240))
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryCalendarDeadlineModel(Base):
    __tablename__ = "regulatory_calendar_deadlines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "destination_id", "deadline_key", name="uq_reg_calendar_deadline_key"),
        Index("ix_reg_calendar_deadline_due", "tenant_id", "status", "due_date"),
    )
    deadline_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("regulatory_destinations.destination_id", ondelete="RESTRICT"), nullable=False)
    deadline_key: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    linked_case_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="SET NULL"))
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatorySupervisoryAuditEventModel(Base):
    __tablename__ = "regulatory_supervisory_audit_events"
    __table_args__ = (UniqueConstraint("tenant_id", "case_id", "sequence", name="uq_reg_supervisory_audit_sequence"),)
    audit_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reconciliation_cases.case_id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(90), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_event_sha256: Mapped[str | None] = mapped_column(String(64))
    event_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
