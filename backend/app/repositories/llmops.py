from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.llmops import AIUsageLedgerModel, AISLOEventModel
from app.models.orchestration import AgentExecutionModel, AgentModelInvocationModel, AgentToolAuditModel, AgentWorkflowEventModel
from app.models.rag import RAGRetrievalRunModel, RAGRetrievalCandidateModel
from app.models.mcp import MCPToolInvocationModel
from app.models.evaluation import EvaluationRunModel


class LLMOpsRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session; self.tenant_id = tenant_id

    def add_usage(self, row: AIUsageLedgerModel):
        self.session.add(row); self.session.flush(); return row

    def add_slo_event(self, row: AISLOEventModel):
        self.session.add(row); self.session.flush(); return row

    def usage_since(self, since: datetime):
        return list(self.session.scalars(select(AIUsageLedgerModel).where(AIUsageLedgerModel.tenant_id == self.tenant_id, AIUsageLedgerModel.occurred_at >= since)))

    def recent_slo_events(self, limit: int = 50):
        return list(self.session.scalars(select(AISLOEventModel).where(AISLOEventModel.tenant_id == self.tenant_id).order_by(AISLOEventModel.occurred_at.desc()).limit(limit)))

    def slo_by_dedupe(self, dedupe_key: str):
        return self.session.scalar(select(AISLOEventModel).where(AISLOEventModel.tenant_id==self.tenant_id,AISLOEventModel.dedupe_key==dedupe_key))

    def agent_executions_since(self, since: datetime):
        return list(self.session.scalars(select(AgentExecutionModel).where(AgentExecutionModel.tenant_id == self.tenant_id, AgentExecutionModel.created_at >= since)))

    def retrieval_runs_since(self, since: datetime):
        return list(self.session.scalars(select(RAGRetrievalRunModel).where(RAGRetrievalRunModel.tenant_id == self.tenant_id, RAGRetrievalRunModel.created_at >= since)))

    def mcp_invocations_since(self, since: datetime):
        return list(self.session.scalars(select(MCPToolInvocationModel).where(MCPToolInvocationModel.tenant_id == self.tenant_id, MCPToolInvocationModel.created_at >= since)))

    def model_invocations_since(self, since: datetime):
        return list(self.session.scalars(select(AgentModelInvocationModel).where(AgentModelInvocationModel.tenant_id == self.tenant_id, AgentModelInvocationModel.created_at >= since)))

    def evaluation_runs_since(self, since: datetime):
        return list(self.session.scalars(select(EvaluationRunModel).where(EvaluationRunModel.tenant_id == self.tenant_id, EvaluationRunModel.created_at >= since)))

    def trace_detail(self, trace_id: str):
        executions=list(self.session.scalars(select(AgentExecutionModel).where(AgentExecutionModel.tenant_id==self.tenant_id,AgentExecutionModel.trace_id==trace_id).order_by(AgentExecutionModel.created_at)))
        workflow_ids=sorted({x.workflow_id for x in executions})
        retrievals=list(self.session.scalars(select(RAGRetrievalRunModel).where(RAGRetrievalRunModel.tenant_id==self.tenant_id,RAGRetrievalRunModel.trace_id==trace_id).order_by(RAGRetrievalRunModel.created_at)))
        retrieval_ids=[x.retrieval_run_id for x in retrievals]
        candidates=list(self.session.scalars(select(RAGRetrievalCandidateModel).where(RAGRetrievalCandidateModel.tenant_id==self.tenant_id,RAGRetrievalCandidateModel.retrieval_run_id.in_(retrieval_ids)).order_by(RAGRetrievalCandidateModel.retrieval_run_id,RAGRetrievalCandidateModel.final_rank))) if retrieval_ids else []
        model_invocations=list(self.session.scalars(select(AgentModelInvocationModel).where(AgentModelInvocationModel.tenant_id==self.tenant_id,AgentModelInvocationModel.workflow_id.in_(workflow_ids)).order_by(AgentModelInvocationModel.created_at))) if workflow_ids else []
        invocation_ids=[x.invocation_id for x in model_invocations]
        agent_tools=list(self.session.scalars(select(AgentToolAuditModel).where(AgentToolAuditModel.tenant_id==self.tenant_id,AgentToolAuditModel.invocation_id.in_(invocation_ids)).order_by(AgentToolAuditModel.created_at))) if invocation_ids else []
        workflow_events=list(self.session.scalars(select(AgentWorkflowEventModel).where(AgentWorkflowEventModel.tenant_id==self.tenant_id,AgentWorkflowEventModel.workflow_id.in_(workflow_ids)).order_by(AgentWorkflowEventModel.workflow_id,AgentWorkflowEventModel.sequence))) if workflow_ids else []
        mcp=list(self.session.scalars(select(MCPToolInvocationModel).where(MCPToolInvocationModel.tenant_id==self.tenant_id,((MCPToolInvocationModel.trace_id==trace_id)|(MCPToolInvocationModel.workflow_id.in_(workflow_ids) if workflow_ids else False))).order_by(MCPToolInvocationModel.created_at)))
        return {
            "agent_executions":executions,"workflow_events":workflow_events,"model_invocations":model_invocations,"agent_tool_audits":agent_tools,
            "retrieval_runs":retrievals,"retrieval_candidates":candidates,"mcp_invocations":mcp,
            "evaluation_runs":list(self.session.scalars(select(EvaluationRunModel).where(EvaluationRunModel.tenant_id==self.tenant_id,EvaluationRunModel.trace_id==trace_id).order_by(EvaluationRunModel.created_at))),
            "usage":list(self.session.scalars(select(AIUsageLedgerModel).where(AIUsageLedgerModel.tenant_id==self.tenant_id,AIUsageLedgerModel.trace_id==trace_id).order_by(AIUsageLedgerModel.occurred_at))),
        }
