from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.appeal_resolution import AppealDecisionPacketModel, AppealDecisionSecondReviewModel, AppealFinalResolutionModel, AppealResolutionAuditEventModel

class AppealResolutionRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def packet(self,packet_id:str,*,for_update=False):
        q=select(AppealDecisionPacketModel).where(AppealDecisionPacketModel.tenant_id==self.tenant_id,AppealDecisionPacketModel.packet_id==packet_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def latest_packet(self,appeal_id:str): return self.session.scalar(select(AppealDecisionPacketModel).where(AppealDecisionPacketModel.tenant_id==self.tenant_id,AppealDecisionPacketModel.appeal_id==appeal_id).order_by(AppealDecisionPacketModel.packet_version.desc()).limit(1))
    def packets(self,appeal_id:str): return list(self.session.scalars(select(AppealDecisionPacketModel).where(AppealDecisionPacketModel.tenant_id==self.tenant_id,AppealDecisionPacketModel.appeal_id==appeal_id).order_by(AppealDecisionPacketModel.packet_version)))
    def second_reviews(self,packet_id:str): return list(self.session.scalars(select(AppealDecisionSecondReviewModel).where(AppealDecisionSecondReviewModel.tenant_id==self.tenant_id,AppealDecisionSecondReviewModel.packet_id==packet_id).order_by(AppealDecisionSecondReviewModel.created_at)))
    def final_resolution(self,appeal_id:str): return self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.appeal_id==appeal_id))
    def audit(self,appeal_id:str): return list(self.session.scalars(select(AppealResolutionAuditEventModel).where(AppealResolutionAuditEventModel.tenant_id==self.tenant_id,AppealResolutionAuditEventModel.appeal_id==appeal_id).order_by(AppealResolutionAuditEventModel.sequence)))
    def next_audit_sequence(self,appeal_id:str)->int:
        n=self.session.scalar(select(func.max(AppealResolutionAuditEventModel.sequence)).where(AppealResolutionAuditEventModel.tenant_id==self.tenant_id,AppealResolutionAuditEventModel.appeal_id==appeal_id)); return int(n or 0)+1
