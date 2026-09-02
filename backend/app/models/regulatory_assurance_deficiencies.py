from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryAssuranceExceptionModel(Base):
    __tablename__="regulatory_assurance_exceptions"
    exception_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    sample_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    test_run_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    control_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    entity_id:Mapped[str|None]=mapped_column(String(128),nullable=True,index=True)
    exception_type:Mapped[str]=mapped_column(String(64),nullable=False)
    deficiency_kind:Mapped[str]=mapped_column(String(32),nullable=False)
    severity_score:Mapped[int]=mapped_column(Integer,nullable=False)
    evidence_refs:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    provenance:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    status:Mapped[str]=mapped_column(String(32),nullable=False,default="open")
    created_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryDeficiencyModel(Base):
    __tablename__="regulatory_assurance_deficiencies"
    __table_args__=(UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_assurance_deficiency_version"),)
    deficiency_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    deficiency_key:Mapped[str]=mapped_column(String(160),nullable=False,index=True)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    control_id:Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    deficiency_kind:Mapped[str]=mapped_column(String(32),nullable=False)
    severity:Mapped[str]=mapped_column(String(24),nullable=False,index=True)
    severity_score:Mapped[int]=mapped_column(Integer,nullable=False)
    exception_ids:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    affected_entities:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    compensating_control:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    remediation_refs:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    repeated_exception_count:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    status:Mapped[str]=mapped_column(String(32),nullable=False,default="candidate")
    payload_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    created_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryEnterpriseIssueModel(Base):
    __tablename__="regulatory_enterprise_assurance_issues"
    issue_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    deficiency_key:Mapped[str]=mapped_column(String(160),nullable=False,index=True)
    issue_type:Mapped[str]=mapped_column(String(48),nullable=False)
    candidate_material_weakness:Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    severity:Mapped[str]=mapped_column(String(24),nullable=False)
    affected_controls:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    affected_entities:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    sla_due_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    status:Mapped[str]=mapped_column(String(32),nullable=False,default="proposed")
    escalated_by_user_id:Mapped[str|None]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=True)
    escalated_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryDeficiencyClosureModel(Base):
    __tablename__="regulatory_deficiency_closures"
    __table_args__=(UniqueConstraint("tenant_id","deficiency_key","closure_version",name="uq_reg_deficiency_closure_version"),)
    closure_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    deficiency_key:Mapped[str]=mapped_column(String(160),nullable=False,index=True)
    closure_version:Mapped[int]=mapped_column(Integer,nullable=False)
    retest_refs:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    conclusion:Mapped[str]=mapped_column(String(32),nullable=False)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    independent:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    closed_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    closed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
