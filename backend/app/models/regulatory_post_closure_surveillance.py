from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PostClosureSurveillanceSignalModel(Base):
    __tablename__ = "post_closure_surveillance_signals"
    signal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recurrence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sustainability_decay_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    control_regression_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cross_entity_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="observed")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryReopenCandidateModel(Base):
    __tablename__ = "regulatory_reopen_candidates"
    __table_args__ = (UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_reopen_candidate_version"),)
    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger: Mapped[str] = mapped_column(String(80), nullable=False)
    matched_closed_finding_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prior_certification_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recurrence_evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    renewed_corrective_action_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    regulator_followup_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False, default="monitor")
    human_decision_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_human_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ReopenedIssueInvestigationModel(Base):
    __tablename__ = "reopened_issue_investigations"
    investigation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    renewed_corrective_action_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    revalidation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    decided_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
