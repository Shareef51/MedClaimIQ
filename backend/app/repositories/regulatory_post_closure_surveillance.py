from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_post_closure_surveillance import *

class RegulatoryPostClosureSurveillanceRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def signals(self,key=None):
        q=select(PostClosureSurveillanceSignalModel).where(PostClosureSurveillanceSignalModel.tenant_id==self.tenant_id)
        if key: q=q.where(PostClosureSurveillanceSignalModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(PostClosureSurveillanceSignalModel.detected_at.desc())))
    def candidates(self,key=None):
        q=select(RegulatoryReopenCandidateModel).where(RegulatoryReopenCandidateModel.tenant_id==self.tenant_id)
        if key: q=q.where(RegulatoryReopenCandidateModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(RegulatoryReopenCandidateModel.version)))
    def candidate(self,cid): return self.session.scalar(select(RegulatoryReopenCandidateModel).where(RegulatoryReopenCandidateModel.tenant_id==self.tenant_id,RegulatoryReopenCandidateModel.candidate_id==cid))
    def investigations(self,key=None):
        q=select(ReopenedIssueInvestigationModel).where(ReopenedIssueInvestigationModel.tenant_id==self.tenant_id)
        if key: q=q.where(ReopenedIssueInvestigationModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(ReopenedIssueInvestigationModel.decided_at.desc())))
