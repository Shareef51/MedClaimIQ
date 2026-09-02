from __future__ import annotations

from dataclasses import replace

import pytest

from app.agents.contracts import AgentContext, AgentRegistry, SpecialistAgent
from app.domain.orchestration import (
    AgentExecutionResult, AgentFinding, AgentName, AgentRunStatus, EvidencePackBinding,
    HumanCheckpoint, HumanCheckpointReason, WorkflowState, WorkflowStatus,
)
from app.orchestration.langgraph_runtime import langgraph_thread_config, parallel_send_payloads
from app.orchestration.retry import RetryPolicy
from app.orchestration.router import ClaimWorkflowRouter
from app.orchestration.state import apply_agent_result, pause_for_human, resume_from_human


def state(**kwargs):
    base = WorkflowState(
        workflow_id="wf-1", tenant_id="tenant-a", claim_id="claim-1", thread_id="thread-1",
        status=WorkflowStatus.RUNNING,
        evidence_pack=EvidencePackBinding("pack-1", "claim-1", "a" * 64),
        selected_agents=(AgentName.INTAKE, AgentName.POLICY, AgentName.CODING),
    )
    return replace(base, **kwargs)


def test_router_selects_hospital_financial_and_coding_specialists_deterministically():
    router = ClaimWorkflowRouter()
    result = router.route(
        source_types=("fhir_eob", "invoice", "coding_reference"),
        has_material_contradiction=False, guardrail_decision="pass", no_evidence=False,
    )
    assert AgentName.HOSPITAL_VERIFICATION in result.selected_agents
    assert AgentName.INVOICE_VERIFICATION in result.selected_agents
    assert AgentName.CODING in result.selected_agents
    assert len(result.selected_agents) == len(set(result.selected_agents))
    assert result.parallel_groups[0] == (AgentName.INTAKE,)


def test_router_preserves_escalation_reason_without_granting_decision_authority():
    result = ClaimWorkflowRouter().route(
        source_types=("policy",), has_material_contradiction=True,
        guardrail_decision="escalate", no_evidence=False,
    )
    assert "material_contradiction" in {r.value for r in result.reasons}
    assert "guardrail_escalation" in {r.value for r in result.reasons}
    assert AgentName.DECISION_SUPPORT not in result.selected_agents


def test_parallel_send_payloads_exclude_intake_and_preserve_workflow_id():
    payloads = parallel_send_payloads(state())
    assert {p["agent"] for p in payloads} == {"policy", "coding"}
    assert all(p["workflow_id"] == "wf-1" for p in payloads)


def test_langgraph_config_uses_stable_thread_and_scoped_metadata():
    config = langgraph_thread_config(state())
    assert config["configurable"]["thread_id"] == "thread-1"
    assert config["metadata"] == {"tenant_id": "tenant-a", "claim_id": "claim-1", "workflow_id": "wf-1"}


def test_retry_policy_is_bounded_exponential_backoff():
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=5, max_delay_seconds=12)
    assert [policy.delay_for_attempt(i) for i in (1, 2, 3)] == [5, 10, 12]
    assert policy.may_retry(attempt=2, retryable=True) is True
    assert policy.may_retry(attempt=3, retryable=True) is False
    assert policy.may_retry(attempt=1, retryable=False) is False


def test_apply_agent_result_reducer_adds_findings_without_overwriting_prior_results():
    finding = AgentFinding(AgentName.POLICY, "finding-1", "Coverage clause supports the service.", .91, ("ev-1",))
    result = AgentExecutionResult(AgentName.POLICY, AgentRunStatus.SUCCEEDED, 1, (finding,))
    updated = apply_agent_result(state(), result)
    assert updated.completed_agents == (AgentName.POLICY,)
    assert updated.findings == (finding,)
    assert updated.state_version == 2


def test_human_interrupt_and_resume_require_exact_checkpoint():
    checkpoint = HumanCheckpoint(
        "hcp-1", HumanCheckpointReason.MATERIAL_CONTRADICTION, "Reviewer must inspect conflict.",
        ("claim:review",), "pack-1",
    )
    paused = pause_for_human(state(), checkpoint)
    assert paused.status == WorkflowStatus.WAITING_HUMAN
    with pytest.raises(ValueError, match="checkpoint"):
        resume_from_human(paused, checkpoint_id="hcp-wrong")
    resumed = resume_from_human(paused, checkpoint_id="hcp-1")
    assert resumed.status == WorkflowStatus.RUNNING
    assert resumed.human_checkpoint is None


def test_evidence_pack_binding_is_immutable():
    binding = state().evidence_pack
    with pytest.raises(Exception):
        binding.pack_id = "pack-other"  # type: ignore[misc]


class FakeAgent(SpecialistAgent):
    name = AgentName.POLICY
    def run(self, *, state, context, attempt):
        return AgentExecutionResult(self.name, AgentRunStatus.SUCCEEDED, attempt)


def test_agent_registry_is_explicit_and_rejects_duplicate_agent_registration():
    registry = AgentRegistry((FakeAgent(),))
    assert registry.get(AgentName.POLICY).name == AgentName.POLICY
    with pytest.raises(ValueError):
        registry.register(FakeAgent())


def test_agent_context_exposes_no_database_or_claim_lifecycle_mutator():
    fields = set(AgentContext.__dataclass_fields__)
    assert fields == {"tenant_id", "claim_id", "workflow_id", "evidence_pack", "trace_id"}
    assert "session" not in fields and "db" not in fields and "decision_service" not in fields


def test_postgres_checkpointer_normalizes_sqlalchemy_psycopg_uri_and_uses_strict_mode():
    from app.orchestration.checkpoint import LangGraphPostgresCheckpointerFactory
    factory = LangGraphPostgresCheckpointerFactory("postgresql+psycopg://u:p@db/medclaimiq")
    assert factory.psycopg_uri(factory.database_uri) == "postgresql://u:p@db/medclaimiq"
    assert factory.strict_msgpack is True
