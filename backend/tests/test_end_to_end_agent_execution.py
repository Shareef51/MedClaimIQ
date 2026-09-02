from __future__ import annotations

import sys
import types
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.db.base import Base
from app.domain.orchestration import AgentExecutionResult, AgentFinding, AgentName, AgentRunStatus
from app.models.claims import ClaimModel
from app.models.cross_source_rag import EvidencePackItemModel, EvidencePackModel
from app.models.tenancy import OrganizationModel, TenantModel
from app.orchestration.engine import EndToEndLangGraphBuilder, WorkflowExecutionNodes, initial_runtime_state
from app.orchestration.evidence_hydration import DatabaseEvidenceSnapshotProvider, EvidenceHydrationError


def _sqlite_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_claim_pack(factory):
    with factory() as db:
        db.add(TenantModel(
            tenant_id="tenant-a", slug="tenant-a", display_name="Tenant A", tenant_type="payer",
            status="active", data_region="local",
        ))
        db.add(OrganizationModel(
            organization_id="org-a", tenant_id="tenant-a", slug="org-a", display_name="Org A",
            organization_type="payer", external_identifiers={}, is_active=True,
        ))
        claim = ClaimModel(
            claim_id="claim-1", tenant_id="tenant-a", external_claim_ref="EXT-1",
            patient_subject_id="patient-1", provider_organization_id="org-a", payer_organization_id="org-a",
            claim_type="medical", status="submitted", status_version=1,
            total_amount=Decimal("125.00"), currency="USD", service_from=date(2026, 8, 1),
        )
        db.add(claim)
        db.flush()
        text = (
            "Claim claim-1: status=submitted; total=125.00 USD; service=2026-08-01 to 2026-08-01; "
            "policy=None; encounter=None."
        )
        db.add(EvidencePackModel(
            pack_id="pack-1", tenant_id="tenant-a", claim_id="claim-1",
            query_sha256="q" * 64, query_length=10, planner_version="test-v1",
            requested_retrievers=["sql"], executed_retrievers=["sql"], evidence_count=1,
            contradiction_count=0, confidence=.98, coverage=1.0, source_diversity=1.0,
            no_evidence=False, unresolved_material_contradictions=0, assessment_reasons=[], trace_id=None,
        ))
        db.add(EvidencePackItemModel(
            item_id="item-1", tenant_id="tenant-a", claim_id="claim-1", pack_id="pack-1",
            evidence_key="ev-claim", rank=1, retriever="sql", source_type="structured_claim_db",
            source_id="claim-1", source_version="1", content_sha256=sha256(text.encode()).hexdigest(),
            authority_rank=78, confidence=.98, citation={"source_id": "claim-1"}, metadata_summary={},
            created_at=datetime.now(UTC),
        ))
        db.commit()
    return text


def test_database_evidence_pack_hydration_reconstructs_and_hash_verifies_source():
    factory = _sqlite_factory()
    expected = _seed_claim_pack(factory)
    from app.domain.orchestration import EvidencePackBinding
    with factory() as db:
        snapshot = DatabaseEvidenceSnapshotProvider(db, "tenant-a").load(
            EvidencePackBinding("pack-1", "claim-1", sha256(f"pack-1|{'q'*64}|1|0|test-v1".encode()).hexdigest())
        )
        assert snapshot.items[0].text == expected
        assert snapshot.evidence_keys == frozenset({"ev-claim"})
        assert snapshot.assessment["confidence"] == .98


def test_database_evidence_pack_hydration_fails_closed_on_source_drift():
    factory = _sqlite_factory()
    _seed_claim_pack(factory)
    from app.domain.orchestration import EvidencePackBinding
    with factory() as db:
        claim = db.get(ClaimModel, "claim-1")
        claim.status = "verifying"
        db.commit()
    with factory() as db, pytest.raises(EvidenceHydrationError, match="source drift"):
        DatabaseEvidenceSnapshotProvider(db, "tenant-a").load(
            EvidencePackBinding("pack-1", "claim-1", sha256(f"pack-1|{'q'*64}|1|0|test-v1".encode()).hexdigest())
        )


class SyntheticNodes(WorkflowExecutionNodes):
    def __init__(self, *, failed_agent: AgentName | None = None):
        self.failed_agent = failed_agent
        self.calls: list[tuple[AgentName, int]] = []
        self.retry_policy = type("P", (), {"max_attempts": 3})()

    def _run_agent(self, state, agent_name):
        prior = len(self._prior_findings(state))
        self.calls.append((agent_name, prior))
        if agent_name == self.failed_agent:
            return AgentExecutionResult(
                agent_name, AgentRunStatus.FAILED, 1, error_code="synthetic_failure", retryable=False
            )
        finding = AgentFinding(
            agent=agent_name, finding_id=f"finding-{agent_name.value}",
            summary=f"{agent_name.value} synthetic finding", confidence=.9,
            evidence_keys=("ev-claim",), requires_human_review=agent_name in {
                AgentName.DECISION_SUPPORT, AgentName.HUMAN_REVIEW_ROUTER,
            },
        )
        return AgentExecutionResult(agent_name, AgentRunStatus.SUCCEEDED, 1, (finding,))

    def human_gate(self, state):
        return {"checkpoint_id": "hcp-synthetic", "human_review_required": True, "current_stage": "human_gate"}


def _merge(state, update):
    out = dict(state)
    if "agent_results" in update:
        out["agent_results"] = list(out.get("agent_results", [])) + list(update["agent_results"])
    for key, value in update.items():
        if key != "agent_results":
            out[key] = value
    return out


def test_synthetic_end_to_end_fan_out_fan_in_runs_all_thirteen_agents_and_review_gate():
    nodes = SyntheticNodes()
    state = initial_runtime_state(workflow_id="wf-1", tenant_id="tenant-a", claim_id="claim-1")
    state["selected_agents"] = [
        AgentName.INTAKE.value,
        AgentName.HOSPITAL_VERIFICATION.value, AgentName.INVOICE_VERIFICATION.value,
        AgentName.ELIGIBILITY.value, AgentName.POLICY.value, AgentName.CODING.value,
        AgentName.DUPLICATE_CLAIM.value, AgentName.FRAUD_WASTE.value, AgentName.DENIAL_RISK.value,
    ]
    state = _merge(state, nodes.supervisor(state))
    state = _merge(state, nodes.intake(state))
    branch_results = []
    for name in state["parallel_agents"]:
        branch_results.extend(nodes.specialist({**state, "active_agent": name})["agent_results"])
    state["agent_results"].extend(branch_results)
    state = _merge(state, nodes.evidence_fusion(state))
    state = _merge(state, nodes.critic(state))
    state = _merge(state, nodes.decision_support(state))
    state = _merge(state, nodes.human_review_router(state))
    state = _merge(state, nodes.human_gate(state))

    assert {name for name, _ in nodes.calls} == set(AgentName)
    assert len(nodes.calls) == 13
    fusion_call = next(item for item in nodes.calls if item[0] == AgentName.EVIDENCE_FUSION)
    assert fusion_call[1] == 9  # intake + eight parallel specialists
    assert state["human_review_required"] is True
    assert state["checkpoint_id"] == "hcp-synthetic"


def test_specialist_failure_is_isolated_and_downstream_critic_and_human_gate_still_run():
    nodes = SyntheticNodes(failed_agent=AgentName.CODING)
    state = initial_runtime_state(workflow_id="wf-1", tenant_id="tenant-a", claim_id="claim-1")
    state["selected_agents"] = [AgentName.INTAKE.value, AgentName.POLICY.value, AgentName.CODING.value]
    state = _merge(state, nodes.supervisor(state))
    state = _merge(state, nodes.intake(state))
    for name in state["parallel_agents"]:
        state = _merge(state, nodes.specialist({**state, "active_agent": name}))
    state = _merge(state, nodes.evidence_fusion(state))
    state = _merge(state, nodes.critic(state))
    state = _merge(state, nodes.decision_support(state))
    state = _merge(state, nodes.human_review_router(state))
    state = _merge(state, nodes.human_gate(state))
    statuses = {item["agent"]: item["status"] for item in state["agent_results"]}
    assert statuses["coding"] == "failed"
    assert statuses["critic"] == "succeeded"
    assert state["checkpoint_id"] == "hcp-synthetic"


def test_compiled_graph_topology_contains_full_production_node_chain(monkeypatch):
    class FakeGraph:
        def __init__(self, _state):
            self.nodes = []
            self.edges = []
            self.conditionals = []
        def add_node(self, name, fn): self.nodes.append(name)
        def add_edge(self, left, right): self.edges.append((left, right))
        def add_conditional_edges(self, left, fn, targets): self.conditionals.append((left, tuple(targets)))
        def compile(self, checkpointer=None): return self

    fake_graph = types.ModuleType("langgraph.graph")
    fake_graph.StateGraph = FakeGraph
    fake_graph.START = "START"
    fake_graph.END = "END"
    fake_types = types.ModuleType("langgraph.types")
    fake_types.Send = lambda node, arg: (node, arg)
    fake_types.interrupt = lambda payload: payload
    monkeypatch.setitem(sys.modules, "langgraph", types.ModuleType("langgraph"))
    monkeypatch.setitem(sys.modules, "langgraph.graph", fake_graph)
    monkeypatch.setitem(sys.modules, "langgraph.types", fake_types)

    graph = EndToEndLangGraphBuilder(SyntheticNodes()).build()
    assert graph.nodes == [
        "hydrate_evidence", "supervisor", "intake", "specialist", "evidence_fusion", "critic",
        "decision_support", "human_review_router", "human_gate",
    ]
    assert ("intake", ("specialist",)) in graph.conditionals
    assert ("critic", "decision_support") in graph.edges
    assert ("human_review_router", "human_gate") in graph.edges
