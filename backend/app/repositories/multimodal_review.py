from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.multimodal_review import MultimodalReviewAnnotationModel


class MultimodalReviewRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def add(self, model: MultimodalReviewAnnotationModel):
        if model.tenant_id != self.tenant_id:
            raise ValueError("tenant mismatch")
        self.session.add(model)
        self.session.flush()
        return model

    def by_idempotency(self, key: str):
        return self.session.scalar(select(MultimodalReviewAnnotationModel).where(
            MultimodalReviewAnnotationModel.tenant_id == self.tenant_id,
            MultimodalReviewAnnotationModel.idempotency_key == key,
        ))

    def list_for_claim(self, claim_id: str):
        return list(self.session.scalars(select(MultimodalReviewAnnotationModel).where(
            MultimodalReviewAnnotationModel.tenant_id == self.tenant_id,
            MultimodalReviewAnnotationModel.claim_id == claim_id,
        ).order_by(MultimodalReviewAnnotationModel.created_at)))
