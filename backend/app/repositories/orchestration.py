from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event
from app.models.orchestration import (
    AgentExecutionModel, AgentFindingModel, AgentHumanCheckpointModel, AgentWorkflowEventModel, AgentWorkflowModel,
    AgentModelInvocationModel, AgentToolAuditModel,
)


class OrchestrationRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def get_workflow(self, workflow_id: str, *, for_update: bool = False) -> AgentWorkflowModel | None:
        stmt = select(AgentWorkflowModel).where(
            AgentWorkflowModel.tenant_id == self.tenant_id,
            AgentWorkflowModel.workflow_id == workflow_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def get_by_workflow_key(self, claim_id: str, workflow_key: str) -> AgentWorkflowModel | None:
        return self.session.scalar(select(AgentWorkflowModel).where(
            AgentWorkflowModel.tenant_id == self.tenant_id,
            AgentWorkflowModel.claim_id == claim_id,
            AgentWorkflowModel.workflow_key == workflow_key,
        ))

    def add_workflow(self, model: AgentWorkflowModel) -> AgentWorkflowModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("workflow tenant mismatch")
        self.session.add(model); self.session.flush(); return model


    def add_execution(self, model: AgentExecutionModel) -> AgentExecutionModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("execution tenant mismatch")
        self.session.add(model); self.session.flush(); return model

    def add_finding(self, model: AgentFindingModel) -> AgentFindingModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("finding tenant mismatch")
        self.session.add(model); self.session.flush(); return model


    def add_model_invocation(self, model: AgentModelInvocationModel) -> AgentModelInvocationModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("model invocation tenant mismatch")
        self.session.add(model); self.session.flush(); return model

    def add_tool_audit(self, model: AgentToolAuditModel) -> AgentToolAuditModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("tool audit tenant mismatch")
        self.session.add(model); self.session.flush(); return model

    def get_checkpoint(self, checkpoint_id: str, *, for_update: bool = False) -> AgentHumanCheckpointModel | None:
        stmt = select(AgentHumanCheckpointModel).where(
            AgentHumanCheckpointModel.tenant_id == self.tenant_id,
            AgentHumanCheckpointModel.checkpoint_id == checkpoint_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def add_checkpoint(self, model: AgentHumanCheckpointModel) -> AgentHumanCheckpointModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("checkpoint tenant mismatch")
        self.session.add(model); self.session.flush(); return model



    def checkpoint_for_reason(self, workflow_id: str, reason: str) -> AgentHumanCheckpointModel | None:
        return self.session.scalar(select(AgentHumanCheckpointModel).where(
            AgentHumanCheckpointModel.tenant_id == self.tenant_id,
            AgentHumanCheckpointModel.workflow_id == workflow_id,
            AgentHumanCheckpointModel.reason == reason,
        ).order_by(AgentHumanCheckpointModel.created_at.desc()).limit(1))

    def waiting_checkpoint(self, workflow_id: str) -> AgentHumanCheckpointModel | None:
        return self.session.scalar(select(AgentHumanCheckpointModel).where(
            AgentHumanCheckpointModel.tenant_id == self.tenant_id,
            AgentHumanCheckpointModel.workflow_id == workflow_id,
            AgentHumanCheckpointModel.status == "waiting",
        ).order_by(AgentHumanCheckpointModel.created_at.desc()).limit(1))

    def events_after(self, workflow_id: str, *, after_sequence: int = 0, limit: int = 100) -> list[AgentWorkflowEventModel]:
        return list(self.session.scalars(select(AgentWorkflowEventModel).where(
            AgentWorkflowEventModel.tenant_id == self.tenant_id,
            AgentWorkflowEventModel.workflow_id == workflow_id,
            AgentWorkflowEventModel.sequence > after_sequence,
        ).order_by(AgentWorkflowEventModel.sequence).limit(max(1, min(limit, 500)))))

    def next_event_sequence(self, workflow_id: str) -> int:
        current = self.session.scalar(select(func.max(AgentWorkflowEventModel.sequence)).where(
            AgentWorkflowEventModel.tenant_id == self.tenant_id,
            AgentWorkflowEventModel.workflow_id == workflow_id,
        ))
        return int(current or 0) + 1

    def add_event(self, model: AgentWorkflowEventModel) -> AgentWorkflowEventModel:
        if model.tenant_id != self.tenant_id:
            raise ValueError("event tenant mismatch")
        self.session.add(model); self.session.flush()
        enqueue_realtime_event(self.session, envelope=EventEnvelope(
            event_id=model.event_id, event_type=model.event_type, tenant_id=model.tenant_id,
            claim_id=model.claim_id, aggregate_type="agent_workflow", aggregate_id=model.workflow_id,
            occurred_at=model.occurred_at, trace_id=model.trace_id, producer="medclaimiq-agent-runtime",
            payload={"actor_type":model.actor_type,"sequence":model.sequence},
            metadata={"workflow_id":model.workflow_id},
        ), topic=EventTopic.AGENTS.value)
        return model
