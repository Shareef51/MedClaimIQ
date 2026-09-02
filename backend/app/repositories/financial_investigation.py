from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.financial_investigation import *

class FinancialInvestigationRepository:
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if getattr(row,"tenant_id",self.tenant_id)!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def case(self,case_id,for_update=False):
        q=select(FinancialInvestigationCaseModel).where(FinancialInvestigationCaseModel.tenant_id==self.tenant_id,FinancialInvestigationCaseModel.case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def cases(self,status=None):
        q=select(FinancialInvestigationCaseModel).where(FinancialInvestigationCaseModel.tenant_id==self.tenant_id)
        if status:q=q.where(FinancialInvestigationCaseModel.status==status)
        return list(self.session.scalars(q.order_by(FinancialInvestigationCaseModel.priority.desc(),FinancialInvestigationCaseModel.created_at)))
    def source_case(self,source_investigation_id):
        return self.session.scalar(select(FinancialInvestigationCaseModel).where(FinancialInvestigationCaseModel.tenant_id==self.tenant_id,FinancialInvestigationCaseModel.source_investigation_id==source_investigation_id))
    def cluster_cases(self,cluster_key):
        return list(self.session.scalars(select(FinancialInvestigationCaseModel).where(FinancialInvestigationCaseModel.tenant_id==self.tenant_id,FinancialInvestigationCaseModel.cluster_key==cluster_key).order_by(FinancialInvestigationCaseModel.created_at)))
    def latest_pack(self,case_id):
        return self.session.scalar(select(FinancialInvestigationEvidencePackModel).where(FinancialInvestigationEvidencePackModel.tenant_id==self.tenant_id,FinancialInvestigationEvidencePackModel.case_id==case_id).order_by(FinancialInvestigationEvidencePackModel.pack_version.desc()).limit(1))
    def lease(self,case_id,for_update=False):
        q=select(FinancialInvestigationLeaseModel).where(FinancialInvestigationLeaseModel.tenant_id==self.tenant_id,FinancialInvestigationLeaseModel.case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def annotations(self,case_id):return list(self.session.scalars(select(FinancialInvestigationAnnotationModel).where(FinancialInvestigationAnnotationModel.tenant_id==self.tenant_id,FinancialInvestigationAnnotationModel.case_id==case_id).order_by(FinancialInvestigationAnnotationModel.created_at)))
    def proposals(self,case_id):return list(self.session.scalars(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==self.tenant_id,FinancialRemediationProposalModel.case_id==case_id).order_by(FinancialRemediationProposalModel.created_at)))
    def tasks(self,case_id=None):
        q=select(FinancialInvestigationTaskModel).where(FinancialInvestigationTaskModel.tenant_id==self.tenant_id)
        if case_id:q=q.where(FinancialInvestigationTaskModel.case_id==case_id)
        return list(self.session.scalars(q.order_by(FinancialInvestigationTaskModel.status,FinancialInvestigationTaskModel.due_at)))
    def audit(self,case_id):return list(self.session.scalars(select(FinancialInvestigationAuditEventModel).where(FinancialInvestigationAuditEventModel.tenant_id==self.tenant_id,FinancialInvestigationAuditEventModel.case_id==case_id).order_by(FinancialInvestigationAuditEventModel.sequence)))
    def next_audit_sequence(self,case_id):return int(self.session.scalar(select(func.max(FinancialInvestigationAuditEventModel.sequence)).where(FinancialInvestigationAuditEventModel.tenant_id==self.tenant_id,FinancialInvestigationAuditEventModel.case_id==case_id)) or 0)+1
