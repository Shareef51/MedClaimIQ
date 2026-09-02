from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.multimodal_agent_orchestration import MultimodalAgentEventModel, MultimodalAgentInvestigationModel


class MultimodalAgentOrchestrationRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)

    def add_investigation(self, row: MultimodalAgentInvestigationModel) -> MultimodalAgentInvestigationModel:
        if row.tenant_id != self.tenant_id: raise PermissionError("cross-tenant multimodal investigation denied")
        self.session.add(row); self.session.flush(); return row

    def add_event(self, row: MultimodalAgentEventModel) -> MultimodalAgentEventModel:
        if row.tenant_id != self.tenant_id: raise PermissionError("cross-tenant multimodal event denied")
        self.session.add(row); self.session.flush(); return row

    def workflow_investigations(self, workflow_id: str):
        return list(self.session.scalars(select(MultimodalAgentInvestigationModel).where(
            MultimodalAgentInvestigationModel.tenant_id==self.tenant_id,
            MultimodalAgentInvestigationModel.workflow_id==workflow_id,
        ).order_by(MultimodalAgentInvestigationModel.created_at, MultimodalAgentInvestigationModel.agent_name)))

    def review_required(self, workflow_id: str):
        return list(self.session.scalars(select(MultimodalAgentInvestigationModel).where(
            MultimodalAgentInvestigationModel.tenant_id==self.tenant_id,
            MultimodalAgentInvestigationModel.workflow_id==workflow_id,
            MultimodalAgentInvestigationModel.human_review_required.is_(True),
        ).order_by(MultimodalAgentInvestigationModel.created_at)))
