from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ReopenedRemediationOutcomeModel(Base):
    __tablename__ = "reopened_remediation_outcomes"
    outcome_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    reopen_investigation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    renewed_remediation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    corrective_action_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    milestone_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prior_root_cause_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    current_root_cause_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cross_entity_scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    renewed_commitment_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="remediating")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReopenedControlRevalidationModel(Base):
    __tablename__ = "reopened_control_revalidations"
    revalidation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    outcome_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    control_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prior_effectiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_effectiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recurrence_containment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retest_evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    independent_evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cross_entity_validation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    independently_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecurrenceClosureAssuranceModel(Base):
    __tablename__ = "recurrence_closure_assurance"
    __table_args__ = (UniqueConstraint("tenant_id", "deficiency_key", "version", name="uq_recurrence_closure_version"),)
    assurance_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    revalidation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sustainability_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    sustainability_evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    second_recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    second_recurrence_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    readiness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blockers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_human_recertification")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReopenedIssueRecertificationModel(Base):
    __tablename__ = "reopened_issue_recertifications"
    recertification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    assurance_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    certification_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    decided_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
