from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.governed_closure import AdjudicationAuditEventModel, DecisionNotificationIntentModel, DecisionSecondReviewModel, ReviewDecisionPacketModel


class GovernedClosureRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)

    def add(self, row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def get_packet(self, packet_id: str, *, for_update=False):
        stmt=select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.packet_id==packet_id)
        if for_update: stmt=stmt.with_for_update()
        return self.session.scalar(stmt)

    def latest_packet(self, claim_id: str, *, for_update=False):
        stmt=select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.claim_id==claim_id).order_by(ReviewDecisionPacketModel.created_at.desc()).limit(1)
        if for_update: stmt=stmt.with_for_update()
        return self.session.scalar(stmt)

    def by_idempotency(self, key: str):
        return self.session.scalar(select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.idempotency_key==key))

    def second_reviews(self, packet_id: str):
        return list(self.session.scalars(select(DecisionSecondReviewModel).where(DecisionSecondReviewModel.tenant_id==self.tenant_id,DecisionSecondReviewModel.packet_id==packet_id).order_by(DecisionSecondReviewModel.created_at)))

    def audit_events(self, claim_id: str):
        return list(self.session.scalars(select(AdjudicationAuditEventModel).where(AdjudicationAuditEventModel.tenant_id==self.tenant_id,AdjudicationAuditEventModel.claim_id==claim_id).order_by(AdjudicationAuditEventModel.sequence)))

    def next_audit_sequence(self, claim_id: str) -> int:
        value=self.session.scalar(select(func.max(AdjudicationAuditEventModel.sequence)).where(AdjudicationAuditEventModel.tenant_id==self.tenant_id,AdjudicationAuditEventModel.claim_id==claim_id))
        return int(value or 0)+1

    def notifications(self, claim_id: str):
        return list(self.session.scalars(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.claim_id==claim_id).order_by(DecisionNotificationIntentModel.created_at)))
