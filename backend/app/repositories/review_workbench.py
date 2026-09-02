from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.review_workbench import ReviewActionEventModel, ReviewClaimLockModel, ReviewDecisionMetadataModel, ReviewerNoteModel, ReviewWorkItemModel


class ReviewWorkbenchRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session; self.tenant_id = tenant_id; set_tenant_context(session, tenant_id)

    def get_work_item(self, claim_id: str, *, for_update=False):
        stmt = select(ReviewWorkItemModel).where(ReviewWorkItemModel.tenant_id==self.tenant_id, ReviewWorkItemModel.claim_id==claim_id)
        if for_update: stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def list_queue(self, *, reviewer_user_id: str | None = None, limit: int = 100):
        stmt = select(ReviewWorkItemModel).where(ReviewWorkItemModel.tenant_id==self.tenant_id, ReviewWorkItemModel.status.in_(["open","assigned","in_review","waiting_evidence"]))
        if reviewer_user_id: stmt = stmt.where(ReviewWorkItemModel.assigned_reviewer_user_id==reviewer_user_id)
        return list(self.session.scalars(stmt.order_by(ReviewWorkItemModel.priority_score.desc(), ReviewWorkItemModel.sla_due_at.asc().nullslast(), ReviewWorkItemModel.created_at).limit(min(max(limit,1),500))))

    def add(self, model):
        if model.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(model); self.session.flush(); return model

    def get_lock(self, claim_id: str, *, for_update=False):
        stmt = select(ReviewClaimLockModel).where(ReviewClaimLockModel.tenant_id==self.tenant_id, ReviewClaimLockModel.claim_id==claim_id)
        if for_update: stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def notes(self, claim_id: str):
        return list(self.session.scalars(select(ReviewerNoteModel).where(ReviewerNoteModel.tenant_id==self.tenant_id, ReviewerNoteModel.claim_id==claim_id).order_by(ReviewerNoteModel.created_at)))

    def events(self, claim_id: str, *, limit=500):
        return list(self.session.scalars(select(ReviewActionEventModel).where(ReviewActionEventModel.tenant_id==self.tenant_id, ReviewActionEventModel.claim_id==claim_id).order_by(ReviewActionEventModel.sequence).limit(limit)))

    def event_by_idempotency(self, key: str):
        return self.session.scalar(select(ReviewActionEventModel).where(ReviewActionEventModel.tenant_id==self.tenant_id, ReviewActionEventModel.idempotency_key==key))

    def next_sequence(self, claim_id: str) -> int:
        value = self.session.scalar(select(func.max(ReviewActionEventModel.sequence)).where(ReviewActionEventModel.tenant_id==self.tenant_id, ReviewActionEventModel.claim_id==claim_id))
        return int(value or 0) + 1
