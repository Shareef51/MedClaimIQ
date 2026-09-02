from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.recovery_operations import *

class RecoveryOperationsRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):self.session.add(row);self.session.flush();return row
    def case(self,case_id,for_update=False):
        q=select(RecoveryCaseModel).where(RecoveryCaseModel.tenant_id==self.tenant_id,RecoveryCaseModel.recovery_case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def source_case(self,proposal_id):return self.session.scalar(select(RecoveryCaseModel).where(RecoveryCaseModel.tenant_id==self.tenant_id,RecoveryCaseModel.source_proposal_id==proposal_id))
    def cases(self):return list(self.session.scalars(select(RecoveryCaseModel).where(RecoveryCaseModel.tenant_id==self.tenant_id).order_by(RecoveryCaseModel.priority.desc(),RecoveryCaseModel.created_at)))
    def pack(self,case_id):return self.session.scalar(select(RecoveryEvidencePackModel).where(RecoveryEvidencePackModel.tenant_id==self.tenant_id,RecoveryEvidencePackModel.recovery_case_id==case_id).order_by(RecoveryEvidencePackModel.pack_version.desc()).limit(1))
    def lease(self,case_id,for_update=False):
        q=select(RecoveryLeaseModel).where(RecoveryLeaseModel.tenant_id==self.tenant_id,RecoveryLeaseModel.recovery_case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def outcomes(self,case_id):return list(self.session.scalars(select(RecoveryOutcomeModel).where(RecoveryOutcomeModel.tenant_id==self.tenant_id,RecoveryOutcomeModel.recovery_case_id==case_id).order_by(RecoveryOutcomeModel.occurred_at)))
    def disputes(self,case_id):return list(self.session.scalars(select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id,ProviderDisputeModel.recovery_case_id==case_id).order_by(ProviderDisputeModel.submitted_at)))
    def correspondence(self,case_id):return list(self.session.scalars(select(RecoveryCorrespondenceModel).where(RecoveryCorrespondenceModel.tenant_id==self.tenant_id,RecoveryCorrespondenceModel.recovery_case_id==case_id).order_by(RecoveryCorrespondenceModel.occurred_at)))
    def tasks(self,case_id=None):
        q=select(RecoveryTaskModel).where(RecoveryTaskModel.tenant_id==self.tenant_id)
        if case_id:q=q.where(RecoveryTaskModel.recovery_case_id==case_id)
        return list(self.session.scalars(q.order_by(RecoveryTaskModel.status,RecoveryTaskModel.due_at)))
    def audit(self,case_id):return list(self.session.scalars(select(RecoveryAuditEventModel).where(RecoveryAuditEventModel.tenant_id==self.tenant_id,RecoveryAuditEventModel.recovery_case_id==case_id).order_by(RecoveryAuditEventModel.sequence)))
    def next_audit_sequence(self,case_id):return int(self.session.scalar(select(func.max(RecoveryAuditEventModel.sequence)).where(RecoveryAuditEventModel.tenant_id==self.tenant_id,RecoveryAuditEventModel.recovery_case_id==case_id)) or 0)+1
