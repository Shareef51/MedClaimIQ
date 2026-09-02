from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.mcp import MCPApprovalRequestModel, MCPToolHealthEventModel, MCPToolInvocationModel
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event


class MCPRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def invocation_by_idempotency(self, key: str) -> MCPToolInvocationModel | None:
        return self.session.scalar(select(MCPToolInvocationModel).where(
            MCPToolInvocationModel.tenant_id == self.tenant_id,
            MCPToolInvocationModel.idempotency_key == key,
        ))


    def list_invocations(self, claim_id: str, *, limit: int = 100) -> list[MCPToolInvocationModel]:
        return list(self.session.scalars(select(MCPToolInvocationModel).where(
            MCPToolInvocationModel.tenant_id == self.tenant_id,
            MCPToolInvocationModel.claim_id == claim_id,
        ).order_by(MCPToolInvocationModel.created_at.desc()).limit(max(1, min(limit, 500)))))

    def add_invocation(self, model: MCPToolInvocationModel) -> MCPToolInvocationModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("MCP invocation tenant mismatch")
        self.session.add(model); self.session.flush()
        enqueue_realtime_event(self.session, envelope=EventEnvelope(
            event_id=model.invocation_id, event_type="mcp.tool.invoked", tenant_id=model.tenant_id,
            claim_id=model.claim_id, aggregate_type="mcp_tool", aggregate_id=model.tool_name,
            occurred_at=model.created_at, trace_id=model.trace_id, producer="medclaimiq-mcp-gateway",
            payload={"tool_name":model.tool_name,"risk_tier":model.risk_tier,"mode":model.mode,"status":model.status,"attempts":model.attempts},
            metadata={"workflow_id":model.workflow_id,"tool_version":model.tool_version},
        ), topic=EventTopic.MCP.value)
        return model

    def get_approval(self, approval_id: str, *, for_update: bool = False) -> MCPApprovalRequestModel | None:
        stmt = select(MCPApprovalRequestModel).where(
            MCPApprovalRequestModel.tenant_id == self.tenant_id,
            MCPApprovalRequestModel.approval_id == approval_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def add_approval(self, model: MCPApprovalRequestModel) -> MCPApprovalRequestModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("MCP approval tenant mismatch")
        self.session.add(model); self.session.flush(); return model

    def add_health_event(self, model: MCPToolHealthEventModel) -> MCPToolHealthEventModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("MCP health event tenant mismatch")
        self.session.add(model); self.session.flush(); return model
