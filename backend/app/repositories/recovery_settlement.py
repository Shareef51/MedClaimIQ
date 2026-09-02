from __future__ import annotations
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.recovery_settlement import *
class RecoverySettlementRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def case(self,settlement_case_id,for_update=False):
        q=select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id,RecoverySettlementCaseModel.settlement_case_id==settlement_case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def by_recovery(self,recovery_case_id):return self.session.scalar(select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id,RecoverySettlementCaseModel.recovery_case_id==recovery_case_id))
    def cases(self):return list(self.session.scalars(select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id).order_by(RecoverySettlementCaseModel.updated_at.desc())))
    def evidence(self,settlement_case_id):return list(self.session.scalars(select(RecoverySettlementEvidenceModel).where(RecoverySettlementEvidenceModel.tenant_id==self.tenant_id,RecoverySettlementEvidenceModel.settlement_case_id==settlement_case_id).order_by(RecoverySettlementEvidenceModel.installment_sequence,RecoverySettlementEvidenceModel.created_at)))
    def correlations(self,settlement_case_id):return list(self.session.scalars(select(RecoveryLedgerCorrelationModel).where(RecoveryLedgerCorrelationModel.tenant_id==self.tenant_id,RecoveryLedgerCorrelationModel.settlement_case_id==settlement_case_id).order_by(RecoveryLedgerCorrelationModel.created_at)))
    def exceptions(self,settlement_case_id):return list(self.session.scalars(select(RecoverySettlementExceptionModel).where(RecoverySettlementExceptionModel.tenant_id==self.tenant_id,RecoverySettlementExceptionModel.settlement_case_id==settlement_case_id).order_by(RecoverySettlementExceptionModel.created_at)))
    def certificate(self,settlement_case_id):return self.session.scalar(select(RecoveryCompletionCertificateModel).where(RecoveryCompletionCertificateModel.tenant_id==self.tenant_id,RecoveryCompletionCertificateModel.settlement_case_id==settlement_case_id))
    def correspondence(self,settlement_case_id):return list(self.session.scalars(select(RecoverySettlementCorrespondenceModel).where(RecoverySettlementCorrespondenceModel.tenant_id==self.tenant_id,RecoverySettlementCorrespondenceModel.settlement_case_id==settlement_case_id).order_by(RecoverySettlementCorrespondenceModel.occurred_at)))
    def tasks(self,settlement_case_id):return list(self.session.scalars(select(RecoverySettlementTaskModel).where(RecoverySettlementTaskModel.tenant_id==self.tenant_id,RecoverySettlementTaskModel.settlement_case_id==settlement_case_id).order_by(RecoverySettlementTaskModel.due_at)))
    def audit(self,settlement_case_id):return list(self.session.scalars(select(RecoverySettlementAuditEventModel).where(RecoverySettlementAuditEventModel.tenant_id==self.tenant_id,RecoverySettlementAuditEventModel.settlement_case_id==settlement_case_id).order_by(RecoverySettlementAuditEventModel.sequence)))
    def next_audit_sequence(self,settlement_case_id):return int(self.session.scalar(select(func.max(RecoverySettlementAuditEventModel.sequence)).where(RecoverySettlementAuditEventModel.tenant_id==self.tenant_id,RecoverySettlementAuditEventModel.settlement_case_id==settlement_case_id)) or 0)+1
