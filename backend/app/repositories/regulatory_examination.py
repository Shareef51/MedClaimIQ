from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_examination import *

class RegulatoryExaminationRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def case(self,case_id,for_update=False):
        q=select(RegulatoryExaminationCaseModel).where(RegulatoryExaminationCaseModel.tenant_id==self.tenant_id,RegulatoryExaminationCaseModel.examination_case_id==case_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def case_by_external(self,ref):return self.session.scalar(select(RegulatoryExaminationCaseModel).where(RegulatoryExaminationCaseModel.tenant_id==self.tenant_id,RegulatoryExaminationCaseModel.external_inquiry_reference==ref))
    def cases(self):return list(self.session.scalars(select(RegulatoryExaminationCaseModel).where(RegulatoryExaminationCaseModel.tenant_id==self.tenant_id).order_by(RegulatoryExaminationCaseModel.updated_at.desc())))
    def requests(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationDocumentRequestModel).where(RegulatoryExaminationDocumentRequestModel.tenant_id==self.tenant_id,RegulatoryExaminationDocumentRequestModel.examination_case_id==case_id).order_by(RegulatoryExaminationDocumentRequestModel.due_at)))
    def packs(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationEvidencePackModel).where(RegulatoryExaminationEvidencePackModel.tenant_id==self.tenant_id,RegulatoryExaminationEvidencePackModel.examination_case_id==case_id).order_by(RegulatoryExaminationEvidencePackModel.pack_version)))
    def pack(self,pack_id):return self.session.scalar(select(RegulatoryExaminationEvidencePackModel).where(RegulatoryExaminationEvidencePackModel.tenant_id==self.tenant_id,RegulatoryExaminationEvidencePackModel.evidence_pack_id==pack_id))
    def responses(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationResponseModel).where(RegulatoryExaminationResponseModel.tenant_id==self.tenant_id,RegulatoryExaminationResponseModel.examination_case_id==case_id).order_by(RegulatoryExaminationResponseModel.response_version)))
    def response(self,response_id):return self.session.scalar(select(RegulatoryExaminationResponseModel).where(RegulatoryExaminationResponseModel.tenant_id==self.tenant_id,RegulatoryExaminationResponseModel.response_id==response_id))
    def correspondence(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationCorrespondenceModel).where(RegulatoryExaminationCorrespondenceModel.tenant_id==self.tenant_id,RegulatoryExaminationCorrespondenceModel.examination_case_id==case_id).order_by(RegulatoryExaminationCorrespondenceModel.created_at)))
    def findings(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationFindingModel).where(RegulatoryExaminationFindingModel.tenant_id==self.tenant_id,RegulatoryExaminationFindingModel.examination_case_id==case_id).order_by(RegulatoryExaminationFindingModel.created_at)))
    def commitments(self,case_id):return list(self.session.scalars(select(RegulatoryRemediationCommitmentModel).where(RegulatoryRemediationCommitmentModel.tenant_id==self.tenant_id,RegulatoryRemediationCommitmentModel.examination_case_id==case_id).order_by(RegulatoryRemediationCommitmentModel.due_at)))
    def audit(self,case_id):return list(self.session.scalars(select(RegulatoryExaminationAuditEventModel).where(RegulatoryExaminationAuditEventModel.tenant_id==self.tenant_id,RegulatoryExaminationAuditEventModel.examination_case_id==case_id).order_by(RegulatoryExaminationAuditEventModel.sequence)))
