from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AppealReconsiderationState(TypedDict, total=False):
    tenant_id: str
    claim_id: str
    appeal_id: str
    thread_id: str
    snapshot_id: str
    reingestion_results: Annotated[list[dict[str, Any]], operator.add]
    comparison_refs: list[str]
    rag_run_id: str
    recommendation_run_id: str
    recommendation: str
    missing_evidence: list[str]
    escalation_reasons: list[str]
    adjudication_authority: str
    current_stage: str
    human_review_required: bool
    checkpoint_id: str
    trace_id: str


class AppealReconsiderationGraphBuilder:
    """LangGraph appeal-support graph that can only terminate at a human interrupt.

    Nodes may validate, re-ingest, compare, retrieve and prepare a non-binding
    recommendation. No graph node accepts or persists a final appeal outcome.
    """
    def __init__(self, *, validate_node, reingest_node, compare_node, retrieve_node, recommend_node, human_gate_node) -> None:
        self.validate_node=validate_node;self.reingest_node=reingest_node;self.compare_node=compare_node
        self.retrieve_node=retrieve_node;self.recommend_node=recommend_node;self.human_gate_node=human_gate_node

    def build(self, *, checkpointer=None):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required for appeal reconsideration orchestration") from exc
        graph=StateGraph(AppealReconsiderationState)
        graph.add_node("validate_evidence",self.validate_node)
        graph.add_node("reingest_multimodal",self.reingest_node)
        graph.add_node("compare_original_vs_new",self.compare_node)
        graph.add_node("appeal_hybrid_retrieval",self.retrieve_node)
        graph.add_node("recommendation_only_agent",self.recommend_node)
        graph.add_node("human_appeal_gate",self.human_gate_node)
        graph.add_edge(START,"validate_evidence")
        graph.add_edge("validate_evidence","reingest_multimodal")
        graph.add_edge("reingest_multimodal","compare_original_vs_new")
        graph.add_edge("compare_original_vs_new","appeal_hybrid_retrieval")
        graph.add_edge("appeal_hybrid_retrieval","recommendation_only_agent")
        graph.add_edge("recommendation_only_agent","human_appeal_gate")
        graph.add_edge("human_appeal_gate",END)
        return graph.compile(checkpointer=checkpointer)


def human_appeal_interrupt(state: AppealReconsiderationState):
    try:
        from langgraph.types import interrupt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langgraph is required for durable appeal interrupts") from exc
    return interrupt({
        "appeal_id":state.get("appeal_id"),"snapshot_id":state.get("snapshot_id"),
        "recommendation_run_id":state.get("recommendation_run_id"),"recommendation":state.get("recommendation"),
        "adjudication_authority":"none","required_actor":"authorized_independent_human_appeal_reviewer",
    })
