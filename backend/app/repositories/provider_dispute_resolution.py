from __future__ import annotations
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.provider_dispute_resolution import *
class ProviderDisputeResolutionRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def packet(self,packet_id,for_update=False):
        q=select(ProviderDisputeDecisionPacketModel).where(ProviderDisputeDecisionPacketModel.tenant_id==self.tenant_id,ProviderDisputeDecisionPacketModel.packet_id==packet_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def packets(self,dispute_id):return list(self.session.scalars(select(ProviderDisputeDecisionPacketModel).where(ProviderDisputeDecisionPacketModel.tenant_id==self.tenant_id,ProviderDisputeDecisionPacketModel.dispute_id==dispute_id).order_by(ProviderDisputeDecisionPacketModel.packet_version)))
    def latest_packet(self,dispute_id):return self.session.scalar(select(ProviderDisputeDecisionPacketModel).where(ProviderDisputeDecisionPacketModel.tenant_id==self.tenant_id,ProviderDisputeDecisionPacketModel.dispute_id==dispute_id).order_by(ProviderDisputeDecisionPacketModel.packet_version.desc()).limit(1))
    def second_reviews(self,packet_id):return list(self.session.scalars(select(ProviderDisputeSecondReviewModel).where(ProviderDisputeSecondReviewModel.tenant_id==self.tenant_id,ProviderDisputeSecondReviewModel.packet_id==packet_id).order_by(ProviderDisputeSecondReviewModel.created_at)))
    def final(self,dispute_id):return self.session.scalar(select(ProviderDisputeFinalResolutionModel).where(ProviderDisputeFinalResolutionModel.tenant_id==self.tenant_id,ProviderDisputeFinalResolutionModel.dispute_id==dispute_id))
    def positions(self,case_id):return list(self.session.scalars(select(RecoveryPositionVersionModel).where(RecoveryPositionVersionModel.tenant_id==self.tenant_id,RecoveryPositionVersionModel.recovery_case_id==case_id).order_by(RecoveryPositionVersionModel.sequence)))
    def next_position_sequence(self,case_id):return int(self.session.scalar(select(func.max(RecoveryPositionVersionModel.sequence)).where(RecoveryPositionVersionModel.tenant_id==self.tenant_id,RecoveryPositionVersionModel.recovery_case_id==case_id)) or 0)+1
    def referrals(self,case_id):return list(self.session.scalars(select(RecoveryAmendmentReferralModel).where(RecoveryAmendmentReferralModel.tenant_id==self.tenant_id,RecoveryAmendmentReferralModel.recovery_case_id==case_id).order_by(RecoveryAmendmentReferralModel.created_at)))
    def audit(self,dispute_id):return list(self.session.scalars(select(ProviderDisputeResolutionAuditEventModel).where(ProviderDisputeResolutionAuditEventModel.tenant_id==self.tenant_id,ProviderDisputeResolutionAuditEventModel.dispute_id==dispute_id).order_by(ProviderDisputeResolutionAuditEventModel.sequence)))
    def next_audit_sequence(self,dispute_id):return int(self.session.scalar(select(func.max(ProviderDisputeResolutionAuditEventModel.sequence)).where(ProviderDisputeResolutionAuditEventModel.tenant_id==self.tenant_id,ProviderDisputeResolutionAuditEventModel.dispute_id==dispute_id)) or 0)+1
