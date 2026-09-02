from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_supervisory_control import *

class RegulatorySupervisoryControlRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def case(self,case_id,for_update=False):
        q=select(RegulatoryReconciliationCaseModel).where(RegulatoryReconciliationCaseModel.tenant_id==self.tenant_id,RegulatoryReconciliationCaseModel.case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def case_for_transmission(self,transmission_id):return self.session.scalar(select(RegulatoryReconciliationCaseModel).where(RegulatoryReconciliationCaseModel.tenant_id==self.tenant_id,RegulatoryReconciliationCaseModel.transmission_id==transmission_id))
    def cases(self):return list(self.session.scalars(select(RegulatoryReconciliationCaseModel).where(RegulatoryReconciliationCaseModel.tenant_id==self.tenant_id).order_by(RegulatoryReconciliationCaseModel.updated_at.desc())))
    def attestations(self,case_id):return list(self.session.scalars(select(RegulatoryDeliveryControlAttestationModel).where(RegulatoryDeliveryControlAttestationModel.tenant_id==self.tenant_id,RegulatoryDeliveryControlAttestationModel.case_id==case_id).order_by(RegulatoryDeliveryControlAttestationModel.attestation_version)))
    def attestation(self,attestation_id):return self.session.scalar(select(RegulatoryDeliveryControlAttestationModel).where(RegulatoryDeliveryControlAttestationModel.tenant_id==self.tenant_id,RegulatoryDeliveryControlAttestationModel.attestation_id==attestation_id))
    def exceptions(self,case_id=None):
        q=select(RegulatoryComplianceExceptionModel).where(RegulatoryComplianceExceptionModel.tenant_id==self.tenant_id)
        if case_id:q=q.where(RegulatoryComplianceExceptionModel.case_id==case_id)
        return list(self.session.scalars(q.order_by(RegulatoryComplianceExceptionModel.created_at.desc())))
    def certifications(self,case_id):return list(self.session.scalars(select(RegulatorySupervisoryCertificationModel).where(RegulatorySupervisoryCertificationModel.tenant_id==self.tenant_id,RegulatorySupervisoryCertificationModel.case_id==case_id).order_by(RegulatorySupervisoryCertificationModel.certification_sequence)))
    def annotations(self,case_id):return list(self.session.scalars(select(RegulatorySupervisorAnnotationModel).where(RegulatorySupervisorAnnotationModel.tenant_id==self.tenant_id,RegulatorySupervisorAnnotationModel.case_id==case_id).order_by(RegulatorySupervisorAnnotationModel.created_at)))
    def correspondence(self,case_id):return list(self.session.scalars(select(RegulatorySupervisorCorrespondenceModel).where(RegulatorySupervisorCorrespondenceModel.tenant_id==self.tenant_id,RegulatorySupervisorCorrespondenceModel.case_id==case_id).order_by(RegulatorySupervisorCorrespondenceModel.created_at)))
    def deadlines(self):return list(self.session.scalars(select(RegulatoryCalendarDeadlineModel).where(RegulatoryCalendarDeadlineModel.tenant_id==self.tenant_id).order_by(RegulatoryCalendarDeadlineModel.due_date)))
    def audit(self,case_id):return list(self.session.scalars(select(RegulatorySupervisoryAuditEventModel).where(RegulatorySupervisoryAuditEventModel.tenant_id==self.tenant_id,RegulatorySupervisoryAuditEventModel.case_id==case_id).order_by(RegulatorySupervisoryAuditEventModel.sequence)))
