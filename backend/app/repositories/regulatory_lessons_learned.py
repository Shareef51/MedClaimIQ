from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_lessons_learned import *


class RegulatoryLessonsLearnedRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def add(self, row):
        if row.tenant_id != self.tenant_id:
            raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def lessons(self, key=None):
        q = select(RegulatoryRemediationLessonModel).where(RegulatoryRemediationLessonModel.tenant_id == self.tenant_id)
        if key: q = q.where(RegulatoryRemediationLessonModel.lesson_key == key)
        return list(self.session.scalars(q.order_by(RegulatoryRemediationLessonModel.created_at.desc())))

    def lesson(self, lesson_id):
        return self.session.scalar(select(RegulatoryRemediationLessonModel).where(RegulatoryRemediationLessonModel.tenant_id == self.tenant_id, RegulatoryRemediationLessonModel.lesson_id == lesson_id))

    def feedback(self):
        return list(self.session.scalars(select(RegulatoryFeedbackObservationModel).where(RegulatoryFeedbackObservationModel.tenant_id == self.tenant_id).order_by(RegulatoryFeedbackObservationModel.effective_at.desc())))

    def proposals(self):
        return list(self.session.scalars(select(ControlImprovementProposalModel).where(ControlImprovementProposalModel.tenant_id == self.tenant_id).order_by(ControlImprovementProposalModel.proposed_at.desc())))

    def proposal(self, proposal_id):
        return self.session.scalar(select(ControlImprovementProposalModel).where(ControlImprovementProposalModel.tenant_id == self.tenant_id, ControlImprovementProposalModel.proposal_id == proposal_id))

    def decisions(self):
        return list(self.session.scalars(select(ControlImprovementDecisionModel).where(ControlImprovementDecisionModel.tenant_id == self.tenant_id).order_by(ControlImprovementDecisionModel.decided_at.desc())))

    def promotions(self):
        return list(self.session.scalars(select(KnowledgePromotionModel).where(KnowledgePromotionModel.tenant_id == self.tenant_id).order_by(KnowledgePromotionModel.promoted_at.desc().nullslast())))
