from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PatientModel(TimestampMixin, Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "patient_subject_id", name="subject_per_tenant"),
        Index("ix_patient_tenant_status", "tenant_id", "status"),
    )

    patient_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_identifiers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    synthetic_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProviderModel(TimestampMixin, Base):
    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_ref", name="provider_ref_per_tenant"),
        Index("ix_provider_tenant_org", "tenant_id", "organization_id"),
    )

    provider_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(60), nullable=False, default="organization")
    external_identifiers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PolicyModel(TimestampMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="valid_window"),
        Index("ix_policy_tenant_subject", "tenant_id", "patient_subject_id"),
        Index("ix_policy_effective_window", "tenant_id", "effective_from", "effective_to"),
    )

    policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payer_organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(180), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_system: Mapped[str] = mapped_column(String(120), nullable=False, default="synthetic")


class EncounterModel(TimestampMixin, Base):
    __tablename__ = "encounters"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="valid_window"),
        Index("ix_encounter_tenant_subject", "tenant_id", "patient_subject_id"),
        Index("ix_encounter_tenant_provider", "tenant_id", "provider_organization_id"),
    )

    encounter_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    encounter_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    encounter_type: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_system: Mapped[str] = mapped_column(String(120), nullable=False, default="synthetic")
    external_identifiers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)


class ClaimModel(TimestampMixin, Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="nonnegative_total"),
        CheckConstraint("service_to IS NULL OR service_to >= service_from", name="valid_service_window"),
        UniqueConstraint("tenant_id", "external_claim_ref", name="external_ref_per_tenant"),
        Index("ix_claim_tenant_patient", "tenant_id", "patient_subject_id"),
        Index("ix_claim_tenant_status", "tenant_id", "status"),
        Index("ix_claim_tenant_reviewer", "tenant_id", "assigned_reviewer_user_id"),
    )

    claim_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_claim_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payer_organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("policies.policy_id", ondelete="SET NULL"), nullable=True, index=True
    )
    encounter_id: Mapped[str | None] = mapped_column(
        ForeignKey("encounters.encounter_id", ondelete="SET NULL"), nullable=True, index=True
    )
    claim_type: Mapped[str] = mapped_column(String(60), nullable=False, default="medical")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="submitted", index=True)
    status_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assigned_reviewer_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    service_from: Mapped[date] = mapped_column(Date, nullable=False)
    service_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_review_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    human_review_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClaimLineModel(TimestampMixin, Base):
    __tablename__ = "claim_lines"
    __table_args__ = (
        CheckConstraint("line_number > 0", name="positive_line_number"),
        CheckConstraint("units > 0", name="positive_units"),
        CheckConstraint("amount >= 0", name="nonnegative_amount"),
        UniqueConstraint("tenant_id", "claim_id", "line_number", name="line_number_per_claim"),
        Index("ix_claim_line_tenant_claim", "tenant_id", "claim_id"),
        Index("ix_claim_line_code", "tenant_id", "code_system", "service_code"),
    )

    claim_line_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code_system: Mapped[str] = mapped_column(String(40), nullable=False)
    service_code: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    units: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("1"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="SET NULL"), nullable=True, index=True
    )


class EvidenceArtifactModel(TimestampMixin, Base):
    __tablename__ = "evidence_artifacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "content_sha256", name="content_per_claim"),
        Index("ix_evidence_tenant_claim", "tenant_id", "claim_id"),
        Index("ix_evidence_tenant_status", "tenant_id", "status"),
        Index("ix_evidence_tenant_document_type", "tenant_id", "document_type"),
    )

    evidence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_system: Mapped[str] = mapped_column(String(120), nullable=False)
    source_locator: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_etag: Mapped[str | None] = mapped_column(String(160), nullable=True)
    storage_version_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="quarantined")
    evidence_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True
    )
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authoritative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    media_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidenceLineageModel(Base):
    __tablename__ = "evidence_lineage"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "child_evidence_id", "parent_evidence_id", "relationship", name="unique_edge"
        ),
        Index("ix_lineage_tenant_child", "tenant_id", "child_evidence_id"),
        Index("ix_lineage_tenant_parent", "tenant_id", "parent_evidence_id"),
    )

    lineage_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False
    )
    parent_evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_artifacts.evidence_id", ondelete="RESTRICT"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(40), nullable=False)
    transformation_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transformation_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transformation_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimStatusEventModel(Base):
    __tablename__ = "claim_status_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="idempotency_per_tenant"),
        UniqueConstraint("tenant_id", "claim_id", "to_version", name="version_per_claim"),
        Index("ix_claim_status_event_claim", "tenant_id", "claim_id", "to_version"),
    )

    status_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(40), nullable=False)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    from_version: Mapped[int] = mapped_column(Integer, nullable=False)
    to_version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HumanReviewDecisionModel(Base):
    __tablename__ = "human_review_decisions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="decision_idempotency_per_tenant"),
        Index("ix_human_decision_claim", "tenant_id", "claim_id", "decided_at"),
    )

    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="audit_idempotency_per_tenant"),
        Index("ix_audit_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        Index("ix_audit_tenant_occurred", "tenant_id", "occurred_at"),
    )

    audit_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(160), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
