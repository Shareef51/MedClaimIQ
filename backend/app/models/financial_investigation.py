from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class FinancialInvestigationCaseModel(Base):
    __tablename__="financial_investigation_cases"
    __table_args__=(
        UniqueConstraint("tenant_id","source_investigation_id",name="uq_fin_case_source_investigation"),
        Index("ix_fin_case_status_priority","tenant_id","status","priority"),
        Index("ix_fin_case_claim","tenant_id","claim_id"),
    )
    case_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    claim_id: Mapped[str]=mapped_column(ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False)
    source_investigation_id: Mapped[str]=mapped_column(ForeignKey("financial_anomaly_investigations.investigation_id",ondelete="RESTRICT"),nullable=False)
    anomaly_code: Mapped[str]=mapped_column(String(100),nullable=False)
    anomaly_score: Mapped[int]=mapped_column(Integer,nullable=False)
    severity: Mapped[str]=mapped_column(String(20),nullable=False)
    case_type: Mapped[str]=mapped_column(String(60),nullable=False)
    cluster_key: Mapped[str]=mapped_column(String(160),nullable=False,index=True)
    provider_organization_id: Mapped[str | None]=mapped_column(String(128))
    status: Mapped[str]=mapped_column(String(40),nullable=False,default="open")
    priority: Mapped[int]=mapped_column(Integer,nullable=False,default=50)
    assigned_investigator_user_id: Mapped[str | None]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="SET NULL"))
    root_cause_code: Mapped[str | None]=mapped_column(String(80))
    root_cause_rationale: Mapped[str | None]=mapped_column(Text)
    ai_recommendation: Mapped[dict | None]=mapped_column(JSON)
    ai_disagreement_rationale: Mapped[str | None]=mapped_column(Text)
    case_version: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    created_by_actor_type: Mapped[str]=mapped_column(String(50),nullable=False)
    created_by_actor_id: Mapped[str | None]=mapped_column(String(128))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    closed_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    closure_reason_code: Mapped[str | None]=mapped_column(String(100))
    closure_rationale: Mapped[str | None]=mapped_column(Text)

class FinancialInvestigationEvidencePackModel(Base):
    __tablename__="financial_investigation_evidence_packs"
    __table_args__=(UniqueConstraint("tenant_id","case_id","pack_version",name="uq_fin_case_pack_version"),)
    evidence_pack_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),nullable=False,index=True)
    pack_version: Mapped[int]=mapped_column(Integer,nullable=False)
    source_watermark_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    evidence_items: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    citations: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    related_case_ids: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    payload_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class FinancialInvestigationLeaseModel(Base):
    __tablename__="financial_investigation_leases"
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    investigator_user_id: Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    lease_token_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    lease_version: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    acquired_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class FinancialInvestigationAnnotationModel(Base):
    __tablename__="financial_investigation_annotations"
    __table_args__=(UniqueConstraint("tenant_id","idempotency_key",name="uq_fin_inv_annotation_idem"),)
    annotation_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),nullable=False,index=True)
    reviewer_user_id: Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    target_type: Mapped[str]=mapped_column(String(60),nullable=False)
    target_id: Mapped[str]=mapped_column(String(128),nullable=False)
    body: Mapped[str]=mapped_column(Text,nullable=False)
    tags: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    body_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    idempotency_key: Mapped[str]=mapped_column(String(128),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class FinancialRemediationProposalModel(Base):
    __tablename__="financial_remediation_proposals"
    __table_args__=(UniqueConstraint("tenant_id","idempotency_key",name="uq_fin_remediation_idem"),Index("ix_fin_remediation_case","tenant_id","case_id","status"))
    proposal_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),nullable=False)
    claim_id: Mapped[str]=mapped_column(ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False)
    remediation_type: Mapped[str]=mapped_column(String(80),nullable=False)
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=Decimal("0"))
    currency: Mapped[str]=mapped_column(String(3),nullable=False)
    reason_code: Mapped[str]=mapped_column(String(100),nullable=False)
    rationale: Mapped[str]=mapped_column(Text,nullable=False)
    evidence_pack_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    root_cause_code: Mapped[str]=mapped_column(String(80),nullable=False)
    material: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    status: Mapped[str]=mapped_column(String(40),nullable=False,default="proposed")
    proposed_by_user_id: Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    approved_by_user_id: Mapped[str | None]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"))
    approval_rationale: Mapped[str | None]=mapped_column(Text)
    referral_type: Mapped[str | None]=mapped_column(String(80))
    referral_id: Mapped[str | None]=mapped_column(String(128))
    payload_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    idempotency_key: Mapped[str]=mapped_column(String(128),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    approved_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))

class FinancialInvestigationTaskModel(Base):
    __tablename__="financial_investigation_tasks"
    __table_args__=(UniqueConstraint("tenant_id","idempotency_key",name="uq_fin_inv_task_idem"),Index("ix_fin_inv_task_queue","tenant_id","status","due_at"))
    task_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),nullable=False)
    task_type: Mapped[str]=mapped_column(String(80),nullable=False)
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="open")
    priority: Mapped[int]=mapped_column(Integer,nullable=False)
    due_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    assigned_user_id: Mapped[str | None]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="SET NULL"))
    idempotency_key: Mapped[str]=mapped_column(String(128),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    completed_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))

class FinancialInvestigationAuditEventModel(Base):
    __tablename__="financial_investigation_audit_events"
    __table_args__=(UniqueConstraint("tenant_id","case_id","sequence",name="uq_fin_inv_audit_sequence"),UniqueConstraint("tenant_id","idempotency_key",name="uq_fin_inv_audit_idem"))
    audit_event_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("financial_investigation_cases.case_id",ondelete="CASCADE"),nullable=False)
    sequence: Mapped[int]=mapped_column(Integer,nullable=False)
    event_type: Mapped[str]=mapped_column(String(100),nullable=False)
    actor_type: Mapped[str]=mapped_column(String(50),nullable=False)
    actor_id: Mapped[str | None]=mapped_column(String(128))
    payload: Mapped[dict]=mapped_column(JSON,nullable=False)
    previous_event_sha256: Mapped[str | None]=mapped_column(String(64))
    event_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    idempotency_key: Mapped[str]=mapped_column(String(160),nullable=False)
    occurred_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class FinancialInvestigationEvaluationCaseModel(Base):
    __tablename__="financial_investigation_evaluation_cases"
    evaluation_case_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    scenario_type: Mapped[str]=mapped_column(String(80),nullable=False)
    input_payload: Mapped[dict]=mapped_column(JSON,nullable=False)
    expected_controls: Mapped[dict]=mapped_column(JSON,nullable=False)
    payload_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
