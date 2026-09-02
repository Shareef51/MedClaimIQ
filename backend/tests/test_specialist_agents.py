from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from app.agents.evidence_tools import EvidenceOnlyToolbox, EvidenceSnapshot, EvidenceSnapshotItem, InMemoryEvidenceSnapshotProvider
from app.agents.model_client import OpenAIResponsesStructuredClient, StructuredModelResponse
from app.agents.prompts import build_prompt_registry
from app.agents.specialists import build_specialist_registry
from app.agents.structured import SpecialistAgentOutput
from app.agents.contracts import AgentContext
from app.domain.orchestration import AgentName, EvidencePackBinding, WorkflowState, WorkflowStatus


class FakeStructuredClient:
    def __init__(self, payload: dict | Exception):
        self.payload = payload
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.payload, Exception):
            raise self.payload
        return StructuredModelResponse(
            parsed=SpecialistAgentOutput.model_validate(self.payload), model=kwargs["model"],
            response_id="resp-test", input_tokens=100, output_tokens=25,
        )


def snapshot():
    return EvidenceSnapshot(
        pack_id="pack-1", claim_id="claim-1",
        items=(
            EvidenceSnapshotItem("ev-policy", "Policy requires prior authorization.", "policy", "policy-1", "v1", 90, .95, {"page": 2}),
            EvidenceSnapshotItem("ev-eob", "EOB shows CPT 99213 amount $125.", "fhir_eob", "eob-1", "2", 92, .94, {"resource": "ExplanationOfBenefit/eob-1"}),
        ),
        contradictions=({"field_name":"amount","severity":"material","status":"open"},),
        assessment={"confidence": .91, "coverage": 1.0},
    )


def workflow():
    return WorkflowState(
        workflow_id="wf-1", tenant_id="tenant-a", claim_id="claim-1", thread_id="thread-1",
        status=WorkflowStatus.RUNNING, evidence_pack=EvidencePackBinding("pack-1", "claim-1", "a"*64),
        selected_agents=tuple(AgentName),
    )


def context():
    return AgentContext("tenant-a", "claim-1", "wf-1", EvidencePackBinding("pack-1", "claim-1", "a"*64))


def output(*, key="ev-policy", confidence=.91, recommendation="no_recommendation", disposition="supported", review=False):
    return {
        "findings": [{
            "summary": "Evidence supports the stated policy requirement.", "confidence": confidence,
            "evidence_keys": [key] if key else [], "disposition": disposition, "risk_flags": [],
            "requires_human_review": review,
        }],
        "recommendation": recommendation, "rationale": "Evidence-only rationale.",
        "overall_confidence": confidence, "requires_human_review": review, "missing_evidence": [],
    }


def test_registry_contains_all_thirteen_specialists():
    registry = build_specialist_registry(model_client=FakeStructuredClient(output()), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    assert set(registry.names()) == set(AgentName)
    assert len(registry.names()) == 13


def test_policy_agent_returns_evidence_bound_finding_and_prompt_metadata():
    client = FakeStructuredClient(output())
    registry = build_specialist_registry(model_client=client, evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    agent = registry.get(AgentName.POLICY)
    result = agent.run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "succeeded"
    assert result.findings[0].evidence_keys == ("ev-policy",)
    assert result.findings[0].metadata["prompt_version"] == "1.0.0"
    assert agent.last_telemetry is not None
    assert agent.last_telemetry.input_tokens == 100
    assert {a["tool_name"] for a in agent.last_telemetry.tool_audit} == {"evidence.list", "contradiction.list"}


def test_unknown_evidence_key_fails_closed_without_retry():
    registry = build_specialist_registry(model_client=FakeStructuredClient(output(key="ev-made-up")), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "failed"
    assert result.retryable is False
    assert result.error_code == "agent_contract_violation"


def test_supported_finding_below_confidence_contract_fails_closed():
    registry = build_specialist_registry(model_client=FakeStructuredClient(output(confidence=.40)), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "failed"
    assert "confidence" in (result.error_message or "")


def test_transient_model_error_is_retryable():
    registry = build_specialist_registry(model_client=FakeStructuredClient(TimeoutError("provider timeout")), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "retry_pending"
    assert result.retryable is True


def test_non_decision_agent_cannot_return_approval_support_recommendation():
    registry = build_specialist_registry(model_client=FakeStructuredClient(output(recommendation="support_approval")), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "failed"
    assert result.retryable is False


def test_decision_support_is_advisory_and_forces_human_review():
    registry = build_specialist_registry(model_client=FakeStructuredClient(output(recommendation="support_approval")), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.DECISION_SUPPORT).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "succeeded"
    assert result.findings[0].requires_human_review is True
    assert result.findings[0].metadata["recommendation"] == "support_approval"


def test_evidence_toolbox_has_no_network_or_mutation_capabilities():
    toolbox = EvidenceOnlyToolbox(snapshot())
    public = {name for name in dir(toolbox) if not name.startswith("_")}
    assert {"list_evidence", "get_evidence", "search_evidence", "list_contradictions"}.issubset(public)
    assert not ({"post", "put", "delete", "execute_sql", "write_file", "switch_tenant"} & public)


def test_prompt_registry_has_unique_keys_versions_hashes_and_tool_allowlists():
    prompts = build_prompt_registry()
    assert len({p.prompt_key for p in prompts.values()}) == 13
    assert {p.version for p in prompts.values()} == {"1.0.0"}
    assert all(len(p.prompt_sha256) == 64 for p in prompts.values())
    assert all("evidence.search" in p.allowed_tools for p in prompts.values())
    assert all("final" in p.system_prompt.lower() for p in prompts.values())


def test_eval_fixture_has_one_case_for_every_agent():
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "sample-data/specialist_agent_eval_cases.json").read_text())
    assert {case["agent"] for case in cases} == {agent.value for agent in AgentName}


class FakeResponses:
    def __init__(self):
        self.kwargs = None
    def create(self, **kwargs):
        self.kwargs = kwargs
        payload = output()
        usage = type("Usage", (), {"input_tokens": 12, "output_tokens": 7})()
        return type("Response", (), {"output_text": json.dumps(payload), "model": "fake", "id": "r1", "usage": usage})()


class FakeOpenAI:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_adapter_requests_strict_json_schema_structured_output():
    fake = FakeOpenAI()
    response = OpenAIResponsesStructuredClient(fake).generate(model="gpt-5.6-terra", instructions="safe", input_text="{}", schema=SpecialistAgentOutput)
    fmt = fake.responses.kwargs["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True
    assert fmt["schema"]["additionalProperties"] is False
    assert response.parsed.findings[0].evidence_keys == ["ev-policy"]


def test_scope_mismatch_fails_closed():
    bad = replace(workflow(), claim_id="claim-other")
    registry = build_specialist_registry(model_client=FakeStructuredClient(output()), evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=bad, context=context(), attempt=1)
    assert result.status.value == "failed" and result.retryable is False

class PrimaryTimeoutThenSuccessClient:
    def __init__(self):
        self.models = []
    def generate(self, **kwargs):
        self.models.append(kwargs["model"])
        if len(self.models) == 1:
            raise TimeoutError("primary unavailable")
        return StructuredModelResponse(
            parsed=SpecialistAgentOutput.model_validate(output()), model=kwargs["model"],
            response_id="fallback-response", input_tokens=90, output_tokens=22,
        )


def test_transient_primary_failure_uses_schema_compatible_fallback_model():
    client = PrimaryTimeoutThenSuccessClient()
    registry = build_specialist_registry(model_client=client, evidence_provider=InMemoryEvidenceSnapshotProvider((snapshot(),)))
    result = registry.get(AgentName.POLICY).run(state=workflow(), context=context(), attempt=1)
    assert result.status.value == "succeeded"
    assert client.models == ["gpt-5.6-terra", "gpt-5.6-luna"]
