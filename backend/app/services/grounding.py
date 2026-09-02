from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Protocol

from app.domain.cross_source_rag import RetrieverKind
from app.domain.grounding import (
    CandidateStatement, GuardedPromptEnvelope, GroundingResult, GuardrailDecision, RepairAttempt,
    StatementSupport,
)
from app.domain.rag import RetrievalScope
from app.guardrails.answerability import AnswerabilityGate, EvidenceQualityGate
from app.guardrails.prompt_envelope import GuardedPromptBuilder
from app.guardrails.prompt_injection import RetrievedContentPromptInjectionScanner
from app.guardrails.statement_grounding import UnsupportedClaimDetector
from app.repositories.grounding import GroundingGuardrailRepository
from app.observability.metrics import record_operation
from app.observability.tracing import traced_operation


class CrossSourceSearchProtocol(Protocol):
    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        requested_retrievers: tuple[RetrieverKind, ...] = (),
        top_k: int = 12,
        graph_max_depth: int = 2,
        trace_id: str | None = None,
    ): ...


@dataclass(frozen=True, slots=True)
class GuardedRAGResult:
    grounding: GroundingResult
    prompt_envelope: GuardedPromptEnvelope


class GroundingGuardrailService:
    VERSION = "rag-grounding-guardrails-v1"

    def __init__(
        self,
        *,
        cross_source: CrossSourceSearchProtocol,
        repository: GroundingGuardrailRepository | None = None,
        injection_scanner: RetrievedContentPromptInjectionScanner | None = None,
        quality_gate: EvidenceQualityGate | None = None,
        answerability_gate: AnswerabilityGate | None = None,
        claim_detector: UnsupportedClaimDetector | None = None,
        prompt_builder: GuardedPromptBuilder | None = None,
    ) -> None:
        self.cross_source = cross_source
        self.repository = repository
        self.injection_scanner = injection_scanner or RetrievedContentPromptInjectionScanner()
        self.quality_gate = quality_gate or EvidenceQualityGate()
        self.answerability_gate = answerability_gate or AnswerabilityGate()
        self.claim_detector = claim_detector or UnsupportedClaimDetector()
        self.prompt_builder = prompt_builder or GuardedPromptBuilder()

    def run(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        candidate_statements: tuple[CandidateStatement, ...] = (),
        requested_retrievers: tuple[RetrieverKind, ...] = (),
        top_k: int = 12,
        graph_max_depth: int = 2,
        max_repairs: int = 2,
        trace_id: str | None = None,
    ) -> GuardedRAGResult:
        if not scope.claim_id:
            raise ValueError("grounding guardrails require claim-scoped retrieval")
        if max_repairs < 0 or max_repairs > 2:
            raise ValueError("max_repairs must be between 0 and 2")
        search = self.cross_source.search(
            query=query, scope=scope, requested_retrievers=requested_retrievers,
            top_k=top_k, graph_max_depth=graph_max_depth, trace_id=trace_id,
        )
        pack = search.pack
        screened, quality, answerability = self._assess(pack)
        repairs: list[RepairAttempt] = []

        all_retrievers = (RetrieverKind.SQL, RetrieverKind.FHIR, RetrieverKind.GRAPH, RetrieverKind.VECTOR)
        for attempt in range(1, max_repairs + 1):
            if not answerability.requires_repair:
                break
            strategy = "broaden_retrievers_and_context" if attempt == 1 else "increase_graph_depth_and_candidate_budget"
            repair_retrievers = all_retrievers
            repaired = self.cross_source.search(
                query=query,
                scope=scope,
                requested_retrievers=repair_retrievers,
                top_k=min(30, max(top_k + 4, top_k * (attempt + 1))),
                graph_max_depth=min(4, graph_max_depth + attempt),
                trace_id=trace_id,
            )
            repaired_screened, repaired_quality, repaired_answerability = self._assess(repaired.pack)
            repairs.append(RepairAttempt(
                attempt_number=attempt,
                strategy=strategy,
                query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                requested_retrievers=tuple(item.value for item in repair_retrievers),
                result_pack_id=repaired.pack.pack_id,
                confidence=repaired_answerability.score,
                answerable=repaired_answerability.answerable,
            ))
            # Prefer a repaired pack only when it improves answerability/quality. Security exclusions are never relaxed.
            if (
                repaired_answerability.answerable
                or repaired_quality.score > quality.score
                or len(repaired_screened.safe_items) > len(screened.safe_items)
            ):
                pack, screened, quality, answerability = (
                    repaired.pack, repaired_screened, repaired_quality, repaired_answerability,
                )
            if repaired_answerability.answerable or repaired_answerability.requires_human_review:
                break

        checks = tuple(
            self.claim_detector.check(statement, screened.safe_items, pack.contradictions)
            for statement in candidate_statements
        )
        escalation: list[str] = []
        if screened.excluded_evidence_keys:
            escalation.append("retrieved_content_prompt_injection_risk")
        if quality.unresolved_material_contradictions:
            escalation.append("unresolved_material_contradiction")
        if not answerability.answerable:
            escalation.append("insufficient_grounded_evidence")
        grounding_failed = any(
            check.support != StatementSupport.SUPPORTED
            or check.citation.status.value != "verified"
            or not check.numeric_integrity
            or not check.medical_code_integrity
            or not check.contradiction_safe
            for check in checks
        )
        if grounding_failed:
            escalation.append("candidate_contains_unsupported_or_invalidly_cited_statement")

        if grounding_failed:
            decision = GuardrailDecision.BLOCK
        elif escalation:
            decision = GuardrailDecision.ESCALATE
        else:
            decision = GuardrailDecision.PASS

        result = GroundingResult(
            run_id=f"grun_{uuid.uuid4().hex}",
            claim_id=scope.claim_id,
            pack=pack,
            screened=screened,
            evidence_quality=quality,
            answerability=answerability,
            statement_checks=checks,
            repairs=tuple(repairs),
            decision=decision,
            escalation_reasons=tuple(dict.fromkeys(escalation)),
            guardrail_version=self.VERSION,
        )
        envelope = self.prompt_builder.build(query=query, pack=pack, screened=screened)
        with traced_operation("rag.guardrail.decision", attributes={"decision":decision.value,"escalation_count":len(escalation),"safety_event":decision.value!="pass"}):
            record_operation(operation="rag.guardrail",status="success" if decision.value=="pass" else decision.value,attributes={"decision":decision.value})
        if self.repository is not None:
            candidate_material = "\n".join(f"{item.statement_id}:{item.text}" for item in candidate_statements)
            self.repository.save_result(
                result,
                query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                query_length=len(query),
                candidate_sha256=hashlib.sha256(candidate_material.encode("utf-8")).hexdigest() if candidate_material else None,
                trace_id=trace_id,
            )
        return GuardedRAGResult(grounding=result, prompt_envelope=envelope)

    def _assess(self, pack):
        screened = self.injection_scanner.screen(pack.items)
        quality = self.quality_gate.assess(pack, screened)
        answerability = self.answerability_gate.assess(pack, quality)
        return screened, quality, answerability


def grounding_guardrail_model_contract() -> dict[str, object]:
    return {
        "trust_boundary": {
            "retrieved_content": "untrusted data, never instructions",
            "prompt_injection_screening": "deterministic external guardrail before model context",
            "suspicious_content": "excluded from model context and escalated",
            "authorization": "tenant/claim/ACL enforcement remains outside the LLM",
        },
        "grounding": {
            "claim_level_answerability_gate": True,
            "evidence_quality_thresholds": True,
            "citation_to_evidence_verification": True,
            "unsupported_statement_detection": True,
            "numeric_integrity_checks": True,
            "medical_code_integrity_checks": True,
            "material_contradictions_must_be_disclosed": True,
        },
        "self_correction": {
            "maximum_repair_attempts": 2,
            "may_broaden_authorized_retrievers": True,
            "may_increase_bounded_graph_depth": True,
            "may_relax_tenant_claim_or_acl_scope": False,
            "failure_behavior": "escalate to human review; never fabricate evidence",
        },
        "generation_control": {
            "retrieved_evidence_is_segregated_and_labeled_untrusted": True,
            "every_material_statement_requires_evidence_key_citations": True,
            "final_medical_or_claim_decision_by_ai": False,
        },
        "privacy": "guardrail telemetry persists query/draft hashes and evidence hashes, not raw reviewer queries or generated draft text",
    }
