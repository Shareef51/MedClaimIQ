from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy.orm import Session, sessionmaker

from app.agents.contracts import AgentRegistry
from app.domain.orchestration import AgentExecutionResult, AgentFinding, AgentName, AgentRunStatus, HumanCheckpointReason, WorkflowStatus
from app.orchestration.retry import RetryPolicy
from app.orchestration.specialist_runtime import SpecialistExecutionCoordinator
from app.repositories.orchestration import OrchestrationRepository
from app.services.orchestration import OrchestrationInvariantError, OrchestrationService


_PARALLEL_SPECIALISTS = frozenset({
    AgentName.HOSPITAL_VERIFICATION,
    AgentName.INVOICE_VERIFICATION,
    AgentName.ELIGIBILITY,
    AgentName.POLICY,
    AgentName.CODING,
    AgentName.DUPLICATE_CLAIM,
    AgentName.FRAUD_WASTE,
    AgentName.DENIAL_RISK,
})


class WorkflowExecutionNodes:
    """Production graph-node implementation around the persisted workflow contract.

    Each node opens its own tenant-scoped transaction. This makes parallel Send branches
    independent failure domains and avoids sharing a SQLAlchemy Session across workers.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker,
        registry_factory: Callable[[Session, str], AgentRegistry],
        multimodal_investigation_factory: Callable[[Session, str], object] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.registry_factory = registry_factory
        self.multimodal_investigation_factory = multimodal_investigation_factory
        self.retry_policy = retry_policy or RetryPolicy()

    def hydrate(self, state: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as db:
            repo = OrchestrationRepository(db, state["tenant_id"])
            workflow = repo.get_workflow(state["workflow_id"])
            if workflow is None or workflow.claim_id != state["claim_id"]:
                raise OrchestrationInvariantError("workflow hydration scope mismatch")
            return {
                "thread_id": workflow.thread_id,
                "evidence_pack_id": workflow.evidence_pack_id,
                "evidence_pack_sha256": workflow.evidence_pack_sha256,
                "selected_agents": list(workflow.selected_agents),
                "failed_agents": list(workflow.failed_agents),
            }

    def supervisor(self, state: dict[str, Any]) -> dict[str, Any]:
        selected = [AgentName(name) for name in state.get("selected_agents", [])]
        parallel = [name.value for name in selected if name in _PARALLEL_SPECIALISTS]
        return {"parallel_agents": parallel, "current_stage": "supervisor"}

    def intake(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self._run_agent(state, AgentName.INTAKE)
        return {"agent_results": [self._result_payload(result)], "current_stage": "intake"}

    def specialist(self, state: dict[str, Any]) -> dict[str, Any]:
        name = AgentName(state["active_agent"])
        if name not in _PARALLEL_SPECIALISTS:
            raise OrchestrationInvariantError(f"agent is not a parallel specialist: {name.value}")
        result = self._run_agent(state, name)
        # Parallel branches only write to reducer-backed agent_results. Failure/review
        # aggregation happens after fan-in to avoid concurrent writes to scalar state keys.
        return {"agent_results": [self._result_payload(result)]}

    def evidence_fusion(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self._run_agent(state, AgentName.EVIDENCE_FUSION)
        return {
            "agent_results": [self._result_payload(result)],
            "fused_result": self._result_payload(result),
            "current_stage": "evidence_fusion",
        }

    def critic(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self._run_agent(state, AgentName.CRITIC)
        requires_review = any(item.requires_human_review for item in result.findings)
        return {
            "agent_results": [self._result_payload(result)],
            "critic_result": self._result_payload(result),
            "human_review_required": bool(state.get("human_review_required")) or requires_review or result.status != AgentRunStatus.SUCCEEDED,
            "current_stage": "critic",
        }

    def decision_support(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self._run_agent(state, AgentName.DECISION_SUPPORT)
        return {
            "agent_results": [self._result_payload(result)],
            "decision_support_result": self._result_payload(result),
            # Decision support is advisory by contract and always routes to a human review gate.
            "human_review_required": True,
            "current_stage": "decision_support",
        }

    def human_review_router(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self._run_agent(state, AgentName.HUMAN_REVIEW_ROUTER)
        required = True
        return {
            "agent_results": [self._result_payload(result)],
            "human_review_router_result": self._result_payload(result),
            "human_review_required": required,
            "current_stage": "human_review_router",
        }

    def human_gate(self, state: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as db:
            service = OrchestrationService(db, state["tenant_id"])
            repo = OrchestrationRepository(db, state["tenant_id"])
            workflow = repo.get_workflow(state["workflow_id"], for_update=True)
            if workflow is None:
                raise OrchestrationInvariantError("workflow missing at human gate")
            from app.repositories.multimodal_agent_orchestration import MultimodalAgentOrchestrationRepository
            mm_rows = MultimodalAgentOrchestrationRepository(db, state["tenant_id"]).review_required(workflow.workflow_id)
            reason = HumanCheckpointReason.FINAL_REVIEW_REQUIRED
            message = "Specialist investigation completed. Human claims review is required."
            metadata = {}
            if mm_rows:
                reasons = {r for row in mm_rows for r in (row.escalation_reasons or [])}
                if "multimodal_conflict" in reasons:
                    reason = HumanCheckpointReason.MULTIMODAL_CONFLICT
                    message = "Material cross-modal evidence conflict requires human claims review."
                elif "missing_required_modality" in reasons:
                    reason = HumanCheckpointReason.MISSING_REQUIRED_MODALITY
                    message = "Required multimodal evidence is missing and requires human claims review."
                metadata = {"multimodal_investigation_ids": [r.investigation_id for r in mm_rows], "multimodal_pack_ids": [r.pack_id for r in mm_rows], "escalation_reasons": sorted(reasons)}
            waiting = repo.checkpoint_for_reason(workflow.workflow_id, reason.value)
            if waiting is None:
                waiting = service.create_checkpoint(
                    workflow=workflow, reason=reason, message=message,
                    idempotency_key=f"human-gate:{workflow.workflow_id}:{reason.value}:{workflow.state_version}",
                    trace_id=state.get("trace_id"), checkpoint_metadata=metadata,
                )
            db.commit()
            return {
                "checkpoint_id": waiting.checkpoint_id,
                "checkpoint_reason": waiting.reason,
                "human_review_required": True,
                "current_stage": "human_gate",
            }

    def _run_agent(self, state: dict[str, Any], agent_name: AgentName) -> AgentExecutionResult:
        last: AgentExecutionResult | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            with self.session_factory() as db:
                registry = self.registry_factory(db, state["tenant_id"])
                coordinator = SpecialistExecutionCoordinator(db, state["tenant_id"], registry)
                multimodal_context = None
                if self.multimodal_investigation_factory is not None:
                    mm_service = self.multimodal_investigation_factory(db, state["tenant_id"])
                    multimodal_context = mm_service.prepare(workflow_id=state["workflow_id"], claim_id=state["claim_id"], agent=agent_name, attempt=attempt, trace_id=state.get("trace_id"))
                result = coordinator.run(
                    workflow_id=state["workflow_id"],
                    agent_name=agent_name,
                    attempt=attempt,
                    trace_id=state.get("trace_id"),
                    max_attempts=self.retry_policy.max_attempts,
                    prior_findings=self._prior_findings(state), multimodal_context=multimodal_context,
                )
                db.commit()
            last = result
            if result.status != AgentRunStatus.RETRY_PENDING:
                return result
            if not self.retry_policy.may_retry(attempt=attempt, retryable=result.retryable):
                break
        assert last is not None
        return last


    @staticmethod
    def _prior_findings(state: dict[str, Any]) -> tuple[AgentFinding, ...]:
        findings: list[AgentFinding] = []
        for result in state.get("agent_results", []):
            for item in result.get("findings", []):
                findings.append(AgentFinding(
                    agent=AgentName(item["agent"]), finding_id=str(item["finding_id"]),
                    summary=str(item["summary"]), confidence=float(item["confidence"]),
                    evidence_keys=tuple(item.get("evidence_keys", ())),
                    risk_flags=tuple(item.get("risk_flags", ())),
                    requires_human_review=bool(item.get("requires_human_review", False)),
                    metadata=dict(item.get("metadata", {})),
                ))
        return tuple(findings)

    @staticmethod
    def _result_payload(result: AgentExecutionResult) -> dict[str, Any]:
        return {
            "agent": result.agent.value,
            "status": result.status.value,
            "attempt": result.attempt,
            "findings": [
                {
                    **asdict(item),
                    "agent": item.agent.value,
                    "evidence_keys": list(item.evidence_keys),
                    "risk_flags": list(item.risk_flags),
                }
                for item in result.findings
            ],
            "error_code": result.error_code,
            "retryable": result.retryable,
        }


class EndToEndLangGraphBuilder:
    """Compile the complete specialist workflow using LangGraph dynamic Send branches."""

    def __init__(self, nodes: WorkflowExecutionNodes) -> None:
        self.nodes = nodes

    @staticmethod
    def _fan_out(state: dict[str, Any]):
        try:
            from langgraph.types import Send
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required for dynamic fan-out") from exc
        return [
            Send("specialist", {**state, "active_agent": name})
            for name in state.get("parallel_agents", [])
        ]

    def build(self, *, checkpointer=None):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required to compile the end-to-end workflow") from exc
        from app.orchestration.langgraph_runtime import LangGraphRuntimeState

        graph = StateGraph(LangGraphRuntimeState)
        graph.add_node("hydrate_evidence", self.nodes.hydrate)
        graph.add_node("supervisor", self.nodes.supervisor)
        graph.add_node("intake", self.nodes.intake)
        graph.add_node("specialist", self.nodes.specialist)
        graph.add_node("evidence_fusion", self.nodes.evidence_fusion)
        graph.add_node("critic", self.nodes.critic)
        graph.add_node("decision_support", self.nodes.decision_support)
        graph.add_node("human_review_router", self.nodes.human_review_router)
        graph.add_node("human_gate", self._interrupting_human_gate)
        graph.add_edge(START, "hydrate_evidence")
        graph.add_edge("hydrate_evidence", "supervisor")
        graph.add_edge("supervisor", "intake")
        graph.add_conditional_edges("intake", self._fan_out, ["specialist"])
        graph.add_edge("specialist", "evidence_fusion")
        graph.add_edge("evidence_fusion", "critic")
        graph.add_edge("critic", "decision_support")
        graph.add_edge("decision_support", "human_review_router")
        graph.add_edge("human_review_router", "human_gate")
        graph.add_edge("human_gate", END)
        return graph.compile(checkpointer=checkpointer)

    def _interrupting_human_gate(self, state: dict[str, Any]) -> dict[str, Any]:
        gate = self.nodes.human_gate(state)
        try:
            from langgraph.types import interrupt
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required for durable human interrupt") from exc
        reviewer_input = interrupt({
            "workflow_id": state["workflow_id"],
            "claim_id": state["claim_id"],
            "checkpoint_id": gate["checkpoint_id"],
            "reason": gate.get("checkpoint_reason", HumanCheckpointReason.FINAL_REVIEW_REQUIRED.value),
            "allowed_actions": ["continue", "request_more_evidence", "cancel"],
        })
        return {**gate, "reviewer_input": reviewer_input, "current_stage": "resumed_after_human"}


def initial_runtime_state(*, workflow_id: str, tenant_id: str, claim_id: str, trace_id: str | None = None) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "trace_id": trace_id,
        "agent_results": [],
        "human_review_required": False,
        "current_stage": "created",
    }
