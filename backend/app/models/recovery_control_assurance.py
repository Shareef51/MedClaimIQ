from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RegulatoryReportingPeriodModel(Base):
    __tablename__ = "regulatory_reporting_periods"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_key", name="uq_regulatory_reporting_period_key"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_regulatory_reporting_period_idem"),
        Index("ix_regulatory_reporting_period_status", "tenant_id", "status", "end_date"),
    )
    reporting_period_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(50), nullable=False)
    report_type: Mapped[str] = mapped_column(String(80), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    accounting_period_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    period_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioControlAttestationModel(Base):
    __tablename__ = "portfolio_control_attestations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "reporting_period_id", "source_watermark_sha256", name="uq_control_attestation_watermark"),
        UniqueConstraint("tenant_id", "reporting_period_id", "attestation_version", name="uq_control_attestation_version"),
        Index("ix_control_attestation_period", "tenant_id", "reporting_period_id", "created_at"),
    )
    attestation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    reporting_period_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reporting_periods.reporting_period_id", ondelete="CASCADE"), nullable=False)
    attestation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    control_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    material_blockers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    control_effectiveness_pct: Mapped[str] = mapped_column(String(20), nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_actor_type: Mapped[str] = mapped_column(String(60), nullable=False)
    created_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatorySubmissionPackageModel(Base):
    __tablename__ = "regulatory_submission_packages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "reporting_period_id", "package_version", name="uq_regulatory_submission_package_version"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_regulatory_submission_package_idem"),
        Index("ix_regulatory_submission_package_status", "tenant_id", "status", "created_at"),
    )
    package_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    reporting_period_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reporting_periods.reporting_period_id", ondelete="RESTRICT"), nullable=False)
    attestation_id: Mapped[str] = mapped_column(ForeignKey("portfolio_control_attestations.attestation_id", ondelete="RESTRICT"), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    correction_of_package_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="RESTRICT"))
    amendment_reason: Mapped[str | None] = mapped_column(Text)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    material_blockers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_watermark_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    locked_manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    maker_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    checker_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    staged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ControlEvidenceSampleModel(Base):
    __tablename__ = "control_evidence_samples"
    __table_args__ = (
        UniqueConstraint("tenant_id", "package_id", "sample_sequence", name="uq_control_evidence_sample_sequence"),
        Index("ix_control_evidence_sample_package", "tenant_id", "package_id", "sample_sequence"),
    )
    sample_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="CASCADE"), nullable=False)
    sample_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    selection_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryCertificationModel(Base):
    __tablename__ = "regulatory_certifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "package_id", name="uq_regulatory_certification_package"),
        UniqueConstraint("tenant_id", "reporting_period_id", "certification_sequence", name="uq_regulatory_certification_sequence"),
        Index("ix_regulatory_certification_chain", "tenant_id", "reporting_period_id", "certification_sequence"),
    )
    certification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    reporting_period_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reporting_periods.reporting_period_id", ondelete="RESTRICT"), nullable=False)
    package_id: Mapped[str] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="RESTRICT"), nullable=False)
    certification_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    maker_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    checker_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    locked_manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_certification_sha256: Mapped[str | None] = mapped_column(String(64))
    certification_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatorySubmissionReceiptModel(Base):
    __tablename__ = "regulatory_submission_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "package_id", name="uq_regulatory_submission_receipt_package"),
        UniqueConstraint("tenant_id", "external_submission_id", name="uq_regulatory_submission_external_id"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_regulatory_submission_receipt_idem"),
    )
    receipt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="RESTRICT"), nullable=False)
    external_submission_id: Mapped[str] = mapped_column(String(180), nullable=False)
    submission_status: Mapped[str] = mapped_column(String(30), nullable=False)
    external_receipt_reference: Mapped[str] = mapped_column(String(240), nullable=False)
    receipt_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    submitted_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryAuditAnnotationModel(Base):
    __tablename__ = "regulatory_audit_annotations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_regulatory_audit_annotation_idem"),
        Index("ix_regulatory_audit_annotation_package", "tenant_id", "package_id", "created_at"),
    )
    annotation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("regulatory_submission_packages.package_id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(60), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryControlAuditEventModel(Base):
    __tablename__ = "regulatory_control_audit_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "reporting_period_id", "sequence", name="uq_regulatory_control_audit_sequence"),
        Index("ix_regulatory_control_audit", "tenant_id", "reporting_period_id", "sequence"),
    )
    audit_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    reporting_period_id: Mapped[str] = mapped_column(ForeignKey("regulatory_reporting_periods.reporting_period_id", ondelete="CASCADE"), nullable=False)
    package_id: Mapped[str | None] = mapped_column(String(128))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_event_sha256: Mapped[str | None] = mapped_column(String(64))
    event_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
