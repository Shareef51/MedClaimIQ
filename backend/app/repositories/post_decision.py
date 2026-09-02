from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.post_decision import (
    AppealCaseModel, AppealReviewAssignmentModel, AppealResolutionModel, AppealSupplementalEvidenceModel,
    CommunicationDeadLetterModel, CommunicationDeliveryAttemptModel, DecisionHistoryVersionModel,
    DecisionNoticeModel, ExternalCorrespondenceModel, PostDecisionTaskModel,
)


class PostDecisionRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)

    def add(self,row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def notice(self,notice_id:str,*,for_update=False):
        stmt=select(DecisionNoticeModel).where(DecisionNoticeModel.tenant_id==self.tenant_id,DecisionNoticeModel.notice_id==notice_id)
        if for_update: stmt=stmt.with_for_update()
        return self.session.scalar(stmt)

    def notices(self,claim_id:str):
        return list(self.session.scalars(select(DecisionNoticeModel).where(DecisionNoticeModel.tenant_id==self.tenant_id,DecisionNoticeModel.claim_id==claim_id).order_by(DecisionNoticeModel.created_at)))

    def appeal(self,appeal_id:str,*,for_update=False):
        stmt=select(AppealCaseModel).where(AppealCaseModel.tenant_id==self.tenant_id,AppealCaseModel.appeal_id==appeal_id)
        if for_update: stmt=stmt.with_for_update()
        return self.session.scalar(stmt)

    def appeals(self,claim_id:str):
        return list(self.session.scalars(select(AppealCaseModel).where(AppealCaseModel.tenant_id==self.tenant_id,AppealCaseModel.claim_id==claim_id).order_by(AppealCaseModel.created_at)))

    def supplemental(self,appeal_id:str):
        return list(self.session.scalars(select(AppealSupplementalEvidenceModel).where(AppealSupplementalEvidenceModel.tenant_id==self.tenant_id,AppealSupplementalEvidenceModel.appeal_id==appeal_id).order_by(AppealSupplementalEvidenceModel.linked_at)))

    def assignments(self,appeal_id:str):
        return list(self.session.scalars(select(AppealReviewAssignmentModel).where(AppealReviewAssignmentModel.tenant_id==self.tenant_id,AppealReviewAssignmentModel.appeal_id==appeal_id).order_by(AppealReviewAssignmentModel.assigned_at)))

    def resolution(self,appeal_id:str):
        return self.session.scalar(select(AppealResolutionModel).where(AppealResolutionModel.tenant_id==self.tenant_id,AppealResolutionModel.appeal_id==appeal_id))

    def history(self,claim_id:str):
        return list(self.session.scalars(select(DecisionHistoryVersionModel).where(DecisionHistoryVersionModel.tenant_id==self.tenant_id,DecisionHistoryVersionModel.claim_id==claim_id).order_by(DecisionHistoryVersionModel.sequence)))

    def next_history_sequence(self,claim_id:str)->int:
        value=self.session.scalar(select(func.max(DecisionHistoryVersionModel.sequence)).where(DecisionHistoryVersionModel.tenant_id==self.tenant_id,DecisionHistoryVersionModel.claim_id==claim_id))
        return int(value or 0)+1

    def correspondence(self,claim_id:str):
        return list(self.session.scalars(select(ExternalCorrespondenceModel).where(ExternalCorrespondenceModel.tenant_id==self.tenant_id,ExternalCorrespondenceModel.claim_id==claim_id).order_by(ExternalCorrespondenceModel.occurred_at)))

    def attempts(self,notification_id:str):
        return list(self.session.scalars(select(CommunicationDeliveryAttemptModel).where(CommunicationDeliveryAttemptModel.tenant_id==self.tenant_id,CommunicationDeliveryAttemptModel.notification_id==notification_id).order_by(CommunicationDeliveryAttemptModel.attempt_number)))

    def dead_letter(self,notification_id:str):
        return self.session.scalar(select(CommunicationDeadLetterModel).where(CommunicationDeadLetterModel.tenant_id==self.tenant_id,CommunicationDeadLetterModel.notification_id==notification_id))

    def tasks(self,*,claim_id:str|None=None,mine:str|None=None,status:str="open",limit:int=100):
        stmt=select(PostDecisionTaskModel).where(PostDecisionTaskModel.tenant_id==self.tenant_id,PostDecisionTaskModel.status==status)
        if claim_id: stmt=stmt.where(PostDecisionTaskModel.claim_id==claim_id)
        if mine: stmt=stmt.where(PostDecisionTaskModel.assigned_reviewer_user_id==mine)
        return list(self.session.scalars(stmt.order_by(PostDecisionTaskModel.priority.desc(),PostDecisionTaskModel.due_at).limit(limit)))
