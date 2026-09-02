from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.advanced_rag import AdvancedRAGEventModel, AdvancedRAGRunModel


class AdvancedRAGRepository:
    def __init__(self, session: Session, *, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def add_run(self, run: AdvancedRAGRunModel, events: list[AdvancedRAGEventModel]) -> None:
        if run.tenant_id != self.tenant_id:
            raise PermissionError("cross-tenant advanced RAG run write denied")
        self.session.add(run)
        for event in events:
            if event.tenant_id != self.tenant_id or event.advanced_run_id != run.advanced_run_id:
                raise PermissionError("cross-tenant advanced RAG event write denied")
            self.session.add(event)
        self.session.flush()

    def get_run(self, run_id: str, *, claim_id: str | None = None) -> AdvancedRAGRunModel | None:
        stmt = select(AdvancedRAGRunModel).where(
            AdvancedRAGRunModel.tenant_id == self.tenant_id,
            AdvancedRAGRunModel.advanced_run_id == run_id,
        )
        if claim_id:
            stmt = stmt.where(AdvancedRAGRunModel.claim_id == claim_id)
        return self.session.scalar(stmt)

    def recent_runs(self, *, claim_id: str, limit: int = 20) -> list[AdvancedRAGRunModel]:
        return list(self.session.scalars(
            select(AdvancedRAGRunModel)
            .where(AdvancedRAGRunModel.tenant_id == self.tenant_id, AdvancedRAGRunModel.claim_id == claim_id)
            .order_by(AdvancedRAGRunModel.created_at.desc())
            .limit(max(1, min(100, limit)))
        ))
