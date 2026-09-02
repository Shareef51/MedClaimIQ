from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.claims import ClaimModel
from app.models.portal import PortalActionEventModel, PortalDocumentRequestModel, PortalSubmissionModel

class PortalRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def claim(self,claim_id:str):
        return self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id))
    def patient_claims(self,subject_id:str):
        return list(self.session.scalars(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.patient_subject_id==subject_id).order_by(ClaimModel.updated_at.desc())))
    def provider_claims(self,organization_id:str):
        return list(self.session.scalars(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.provider_organization_id==organization_id).order_by(ClaimModel.updated_at.desc())))
    def requests(self,claim_id:str):
        return list(self.session.scalars(select(PortalDocumentRequestModel).where(PortalDocumentRequestModel.tenant_id==self.tenant_id,PortalDocumentRequestModel.claim_id==claim_id).order_by(PortalDocumentRequestModel.created_at.desc())))
    def request(self,request_id:str):
        return self.session.scalar(select(PortalDocumentRequestModel).where(PortalDocumentRequestModel.tenant_id==self.tenant_id,PortalDocumentRequestModel.request_id==request_id))
    def request_by_decision(self,decision_id:str):
        return self.session.scalar(select(PortalDocumentRequestModel).where(PortalDocumentRequestModel.tenant_id==self.tenant_id,PortalDocumentRequestModel.source_decision_id==decision_id))
    def submissions(self,claim_id:str):
        return list(self.session.scalars(select(PortalSubmissionModel).where(PortalSubmissionModel.tenant_id==self.tenant_id,PortalSubmissionModel.claim_id==claim_id).order_by(PortalSubmissionModel.created_at.desc())))
    def submission_by_upload(self,upload_session_id:str):
        return self.session.scalar(select(PortalSubmissionModel).where(PortalSubmissionModel.tenant_id==self.tenant_id,PortalSubmissionModel.upload_session_id==upload_session_id))
    def submission_by_idempotency(self,key:str):
        return self.session.scalar(select(PortalSubmissionModel).where(PortalSubmissionModel.tenant_id==self.tenant_id,PortalSubmissionModel.idempotency_key==key))
    def event_by_idempotency(self,key:str):
        return self.session.scalar(select(PortalActionEventModel).where(PortalActionEventModel.tenant_id==self.tenant_id,PortalActionEventModel.idempotency_key==key))
