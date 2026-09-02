from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.domain.orchestration import AgentName, WorkflowState


class LangGraphRuntimeState(TypedDict, total=False):
    workflow_id: str
    tenant_id: str
    claim_id: str
    thread_id: str
    selected_agents: list[str]
    parallel_agents: list[str]
    active_agent: str
    agent_results: Annotated[list[dict[str, Any]], operator.add]
    fused_findings: list[dict[str, Any]]
    critic_result: dict[str, Any]
    decision_support_result: dict[str, Any]
    human_review_router_result: dict[str, Any]
    human_review_required: bool
    checkpoint_id: str
    checkpoint_reason: str
    evidence_pack_id: str
    evidence_pack_sha256: str
    current_stage: str
    reviewer_input: dict[str, Any]
    trace_id: str


class LangGraphWorkflowBuilder:
    """Compile a LangGraph StateGraph with dynamic fan-out/fan-in and checkpointing."""

    def __init__(self, *, router_node, agent_node, fusion_node, critic_node, human_gate_node) -> None:
        self.router_node = router_node
        self.agent_node = agent_node
        self.fusion_node = fusion_node
        self.critic_node = critic_node
        self.human_gate_node = human_gate_node

    @staticmethod
    def _fan_out(state: LangGraphRuntimeState):
        try:
            from langgraph.types import Send
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required for dynamic Send fan-out") from exc
        agents = state.get("selected_agents", [])
        return [Send("specialist", {**state, "active_agent": name}) for name in agents if name != AgentName.INTAKE.value]

    def build(self, *, checkpointer=None):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required to compile the workflow") from exc

        graph = StateGraph(LangGraphRuntimeState)
        graph.add_node("supervisor", self.router_node)
        graph.add_node("specialist", self.agent_node)
        graph.add_node("evidence_fusion", self.fusion_node)
        graph.add_node("critic", self.critic_node)
        graph.add_node("human_gate", self.human_gate_node)
        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges("supervisor", self._fan_out, ["specialist"])
        # LangGraph's super-step semantics plus the agent_results reducer provide fan-in
        # before evidence fusion consumes the parallel specialist outputs.
        graph.add_edge("specialist", "evidence_fusion")
        graph.add_edge("evidence_fusion", "critic")
        graph.add_edge("critic", "human_gate")
        graph.add_edge("human_gate", END)
        return graph.compile(checkpointer=checkpointer)


def langgraph_interrupt(payload: dict[str, Any]) -> Any:
    """Durably pause the graph; resumed input becomes this call's return value."""
    try:
        from langgraph.types import interrupt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langgraph is required for interrupt/resume") from exc
    return interrupt(payload)


def langgraph_thread_config(state: WorkflowState) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": state.thread_id},
        "metadata": {"tenant_id": state.tenant_id, "claim_id": state.claim_id, "workflow_id": state.workflow_id},
    }


def parallel_send_payloads(state: WorkflowState) -> tuple[dict[str, Any], ...]:
    return tuple(
        {"node": "specialist", "agent": agent.value, "workflow_id": state.workflow_id}
        for agent in state.selected_agents
        if agent != AgentName.INTAKE
    )
