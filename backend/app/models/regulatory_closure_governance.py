from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryClosurePackageModel(Base):
    __tablename__ = "regulatory_closure_packages"
    package_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    corrective_action_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retest_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    independent_validation_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    regulatory_commitment_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    unresolved_exceptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    compensating_control_exit: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    residual_risk: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryClosureCertificationModel(Base):
    __tablename__ = "regulatory_closure_certifications"
    __table_args__ = (UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_closure_cert_version"),)
    certification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    human_certification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    certified_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatorySustainabilityWindowModel(Base):
    __tablename__ = "regulatory_sustainability_windows"
    window_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    required_observations: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    observed_passes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recurrence_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="monitoring")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class RegulatoryReopenDecisionModel(Base):
    __tablename__ = "regulatory_reopen_decisions"
    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    deficiency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
