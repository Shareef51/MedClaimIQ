from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryControlTestPlanModel(Base):
    __tablename__="regulatory_control_test_plans"
    __table_args__=(UniqueConstraint("tenant_id","control_id","plan_version",name="uq_reg_control_test_plan_version"),)
    test_plan_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    control_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    test_type:Mapped[str]=mapped_column(String(48),nullable=False)
    frequency:Mapped[str]=mapped_column(String(40),nullable=False)
    plan_version:Mapped[int]=mapped_column(Integer,nullable=False)
    sampling_strategy:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    evidence_requirements:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    independent_tester_role:Mapped[str]=mapped_column(String(80),nullable=False)
    active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryControlTestRunModel(Base):
    __tablename__="regulatory_control_test_runs"
    test_run_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    test_plan_id:Mapped[str]=mapped_column(ForeignKey("regulatory_control_test_plans.test_plan_id",ondelete="RESTRICT"),nullable=False,index=True)
    control_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    test_window_start:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    test_window_end:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    population_size:Mapped[int]=mapped_column(Integer,nullable=False)
    population_watermark_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    status:Mapped[str]=mapped_column(String(32),nullable=False,default="prepared")
    scheduled_retest_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    prepared_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryEvidenceSampleModel(Base):
    __tablename__="regulatory_evidence_samples"
    __table_args__=(UniqueConstraint("tenant_id","test_run_id","sample_key",name="uq_reg_evidence_sample_key"),)
    sample_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    test_run_id:Mapped[str]=mapped_column(ForeignKey("regulatory_control_test_runs.test_run_id",ondelete="CASCADE"),nullable=False,index=True)
    sample_key:Mapped[str]=mapped_column(String(160),nullable=False)
    entity_id:Mapped[str|None]=mapped_column(String(128),nullable=True,index=True)
    risk_score:Mapped[int]=mapped_column(Integer,nullable=False)
    selection_reason:Mapped[str]=mapped_column(Text,nullable=False)
    evidence_refs:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    provenance:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    result:Mapped[str]=mapped_column(String(24),nullable=False,default="pending")
    exception_code:Mapped[str|None]=mapped_column(String(80),nullable=True)
    tested_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class RegulatoryControlTestConclusionModel(Base):
    __tablename__="regulatory_control_test_conclusions"
    __table_args__=(UniqueConstraint("tenant_id","test_run_id","conclusion_version",name="uq_reg_test_conclusion_version"),)
    conclusion_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    test_run_id:Mapped[str]=mapped_column(ForeignKey("regulatory_control_test_runs.test_run_id",ondelete="RESTRICT"),nullable=False,index=True)
    conclusion_version:Mapped[int]=mapped_column(Integer,nullable=False)
    effectiveness:Mapped[str]=mapped_column(String(48),nullable=False)
    exception_summary:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    independent:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    concluded_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    concluded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
