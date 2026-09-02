from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from app.agents.contracts import AgentContext, AgentRegistry, SpecialistAgent
from app.agents.evidence_tools import EvidenceOnlyToolbox, EvidenceSnapshot, EvidenceSnapshotProvider
from app.agents.model_client import StructuredModelClient, StructuredModelResponse
from app.agents.prompts import AgentPromptSpec, build_prompt_registry
from app.agents.structured import RecommendationKind, SpecialistAgentOutput
from app.domain.orchestration import AgentExecutionResult, AgentFinding, AgentName, AgentRunStatus, WorkflowState


class AgentContractViolation(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentInvocationTelemetry:
    agent: AgentName
    model: str
    prompt_key: str
    prompt_version: str
    prompt_sha256: str
    input_context_sha256: str
    output_sha256: str
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    tool_audit: tuple[dict[str, object], ...]


class EvidenceBoundSpecialistAgent(SpecialistAgent):
    def __init__(
        self,
        *,
        spec: AgentPromptSpec,
        model_client: StructuredModelClient,
        evidence_provider: EvidenceSnapshotProvider,
    ) -> None:
        self.name = spec.agent
        self.spec = spec
        self.model_client = model_client
        self.evidence_provider = evidence_provider
        self.last_telemetry: AgentInvocationTelemetry | None = None

    def run(self, *, state: WorkflowState, context: AgentContext, attempt: int) -> AgentExecutionResult:
        try:
            snapshot = self.evidence_provider.load(context.evidence_pack)
            self._validate_scope(state, context, snapshot)
            toolbox = EvidenceOnlyToolbox(snapshot)
            evidence = toolbox.list_evidence()
            contradictions = toolbox.list_contradictions()
            prompt_input = self._build_input(state, context, snapshot, evidence, contradictions)
            try:
                response = self.model_client.generate(
                    model=self.spec.model,
                    instructions=self.spec.system_prompt,
                    input_text=prompt_input,
                    schema=SpecialistAgentOutput,
                )
            except (TimeoutError, ConnectionError):
                if not self.spec.fallback_model:
                    raise
                response = self.model_client.generate(
                    model=self.spec.fallback_model,
                    instructions=self.spec.system_prompt,
                    input_text=prompt_input,
                    schema=SpecialistAgentOutput,
                )
            output = response.parsed
            if not isinstance(output, SpecialistAgentOutput):
                output = SpecialistAgentOutput.model_validate(output)
            findings = self._validate_and_convert(output, snapshot, state.multimodal_context)
            output_json = output.model_dump_json()
            self.last_telemetry = AgentInvocationTelemetry(
                agent=self.name, model=response.model, prompt_key=self.spec.prompt_key,
                prompt_version=self.spec.version, prompt_sha256=self.spec.prompt_sha256,
                input_context_sha256=sha256(prompt_input.encode()).hexdigest(),
                output_sha256=sha256(output_json.encode()).hexdigest(), response_id=response.response_id,
                input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                tool_audit=tuple({
                    "tool_name": item.tool_name, "input_sha256": item.input_sha256,
                    "result_sha256": item.result_sha256, "result_count": item.result_count,
                } for item in toolbox.audit),
            )
            return AgentExecutionResult(self.name, AgentRunStatus.SUCCEEDED, attempt, tuple(findings))
        except AgentContractViolation as exc:
            return AgentExecutionResult(
                self.name, AgentRunStatus.FAILED, attempt, error_code="agent_contract_violation",
                error_message=str(exc), retryable=False,
            )
        except (TimeoutError, ConnectionError) as exc:
            return AgentExecutionResult(
                self.name, AgentRunStatus.RETRY_PENDING, attempt, error_code="model_transient_error",
                error_message=str(exc), retryable=True,
            )
        except Exception as exc:
            # Model/provider parsing failures can be retried within the orchestration ceiling.
            return AgentExecutionResult(
                self.name, AgentRunStatus.RETRY_PENDING, attempt, error_code="agent_execution_error",
                error_message=str(exc), retryable=True,
            )

    @staticmethod
    def _validate_scope(state: WorkflowState, context: AgentContext, snapshot: EvidenceSnapshot) -> None:
        if context.tenant_id != state.tenant_id or context.claim_id != state.claim_id:
            raise AgentContractViolation("agent context scope differs from workflow scope")
        if context.evidence_pack.pack_id != state.evidence_pack.pack_id:
            raise AgentContractViolation("agent context evidence pack differs from workflow binding")
        if snapshot.pack_id != context.evidence_pack.pack_id or snapshot.claim_id != context.claim_id:
            raise AgentContractViolation("evidence snapshot scope mismatch")

    def _build_input(self, state, context, snapshot, evidence, contradictions) -> str:
        previous = [
            {
                "agent": finding.agent.value,
                "summary": finding.summary,
                "confidence": finding.confidence,
                "evidence_keys": list(finding.evidence_keys),
                "risk_flags": list(finding.risk_flags),
                "metadata": finding.metadata,
            }
            for finding in state.findings
        ]
        payload = {
            "workflow": {"workflow_id": context.workflow_id, "claim_id": context.claim_id},
            "evidence_pack": {
                "pack_id": snapshot.pack_id,
                "assessment": snapshot.assessment,
                "items": [
                    {
                        "evidence_key": item.evidence_key, "source_type": item.source_type,
                        "source_id": item.source_id, "source_version": item.source_version,
                        "authority_rank": item.authority_rank, "confidence": item.confidence,
                        "citation": item.citation, "text": item.text,
                    }
                    for item in evidence
                ],
                "contradictions": list(contradictions),
            },
            "prior_agent_findings": previous,
            "multimodal_evidence": state.multimodal_context.prompt_payload() if state.multimodal_context else None,
            "allowed_tools": list(self.spec.allowed_tools),
            "output_requirements": {
                "minimum_confidence_for_positive_claim": self.spec.minimum_confidence,
                "every_material_finding_requires_evidence_keys": True,
                "final_claim_decision_prohibited": True,
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def _validate_and_convert(self, output: SpecialistAgentOutput, snapshot: EvidenceSnapshot, multimodal_context=None) -> list[AgentFinding]:
        known = set(snapshot.evidence_keys)
        if multimodal_context is not None:
            known.update(multimodal_context.evidence_keys)
        if output.recommendation in {RecommendationKind.SUPPORT_APPROVAL, RecommendationKind.SUPPORT_DENIAL} and self.name != AgentName.DECISION_SUPPORT:
            raise AgentContractViolation("non-decision-support agent returned decision-support recommendation")
        findings: list[AgentFinding] = []
        for raw in output.findings:
            unknown = set(raw.evidence_keys) - known
            if unknown:
                raise AgentContractViolation(f"finding references unknown evidence keys: {sorted(unknown)}")
            if raw.disposition.value not in {"insufficient_evidence", "review_required"} and not raw.evidence_keys:
                raise AgentContractViolation("material finding is missing evidence keys")
            if raw.confidence < self.spec.minimum_confidence and raw.disposition.value == "supported":
                raise AgentContractViolation("supported finding is below agent confidence contract")
            review = raw.requires_human_review or output.requires_human_review
            if output.recommendation in {RecommendationKind.SUPPORT_APPROVAL, RecommendationKind.SUPPORT_DENIAL}:
                review = True
            findings.append(AgentFinding(
                agent=self.name, finding_id=f"af_{uuid4().hex}", summary=raw.summary,
                confidence=raw.confidence, evidence_keys=tuple(raw.evidence_keys),
                risk_flags=tuple(raw.risk_flags), requires_human_review=review,
                metadata={
                    "disposition": raw.disposition.value,
                    "recommendation": output.recommendation.value,
                    "prompt_key": self.spec.prompt_key,
                    "prompt_version": self.spec.version,
                    "missing_evidence": list(output.missing_evidence),
                },
            ))
        return findings


def build_specialist_registry(
    *, model_client: StructuredModelClient, evidence_provider: EvidenceSnapshotProvider,
    model: str = "gpt-5.6-terra", fallback_model: str | None = "gpt-5.6-luna",
    prompt_version: str = "1.0.0", role_overrides: dict[str, str] | None = None,
) -> AgentRegistry:
    prompts = build_prompt_registry(model=model, fallback_model=fallback_model, version=prompt_version, role_overrides=role_overrides)
    return AgentRegistry(tuple(
        EvidenceBoundSpecialistAgent(spec=prompts[name], model_client=model_client, evidence_provider=evidence_provider)
        for name in AgentName
    ))
