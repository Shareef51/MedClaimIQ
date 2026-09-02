from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryDeficiencyInvestigationModel(Base):
    __tablename__ = "regulatory_deficiency_investigations"
    investigation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    enterprise_issue_id: Mapped[str|None] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    candidate_classification: Mapped[str] = mapped_column(String(48), nullable=False)
    cross_control_impacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    root_cause_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="under_review")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryDeficiencyDispositionModel(Base):
    __tablename__ = "regulatory_deficiency_dispositions"
    __table_args__ = (UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_deficiency_disposition_version"),)
    disposition_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[str] = mapped_column(String(48), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    independent_challenge: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    decided_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryCorrectiveActionPlanModel(Base):
    __tablename__ = "regulatory_corrective_action_plans"
    plan_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    milestones: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    regulatory_commitment_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    compensating_control: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    approved_by_user_id: Mapped[str|None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    approved_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryExecutiveAttestationModel(Base):
    __tablename__ = "regulatory_deficiency_executive_attestations"
    __table_args__ = (UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_deficiency_exec_attestation_version"),)
    attestation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    independent_validation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retest_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    human_attestation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attested_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
