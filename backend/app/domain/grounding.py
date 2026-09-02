from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any

from app.domain.cross_source_rag import EvidenceItem, EvidencePack


class InjectionRisk(StrEnum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class GuardrailDecision(StrEnum):
    PASS = "pass"
    REPAIR = "repair"
    ESCALATE = "escalate"
    BLOCK = "block"


class StatementSupport(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


class CitationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class PromptInjectionFinding:
    evidence_key: str
    risk: InjectionRisk
    score: float
    rule_ids: tuple[str, ...]
    action: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class ScreenedEvidence:
    safe_items: tuple[EvidenceItem, ...]
    findings: tuple[PromptInjectionFinding, ...]
    excluded_evidence_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceQualityAssessment:
    score: float
    qualifying_evidence_count: int
    authoritative_evidence_count: int
    source_type_count: int
    excluded_injection_count: int
    unresolved_material_contradictions: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnswerabilityAssessment:
    answerable: bool
    score: float
    reasons: tuple[str, ...]
    requires_repair: bool
    requires_human_review: bool


@dataclass(frozen=True, slots=True)
class CandidateCitation:
    evidence_key: str
    source_id: str | None = None
    source_version: str | None = None
    locator: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CandidateStatement:
    statement_id: str
    text: str
    citations: tuple[CandidateCitation, ...] = ()

    @property
    def sha256(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CitationVerification:
    status: CitationStatus
    verified_evidence_keys: tuple[str, ...]
    invalid_evidence_keys: tuple[str, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StatementGrounding:
    statement_id: str
    statement_sha256: str
    support: StatementSupport
    support_score: float
    citation: CitationVerification
    numeric_integrity: bool
    medical_code_integrity: bool
    contradiction_safe: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RepairAttempt:
    attempt_number: int
    strategy: str
    query_sha256: str
    requested_retrievers: tuple[str, ...]
    result_pack_id: str | None
    confidence: float
    answerable: bool


@dataclass(frozen=True, slots=True)
class GroundingResult:
    run_id: str
    claim_id: str
    pack: EvidencePack
    screened: ScreenedEvidence
    evidence_quality: EvidenceQualityAssessment
    answerability: AnswerabilityAssessment
    statement_checks: tuple[StatementGrounding, ...]
    repairs: tuple[RepairAttempt, ...]
    decision: GuardrailDecision
    escalation_reasons: tuple[str, ...]
    guardrail_version: str


@dataclass(frozen=True, slots=True)
class GuardedPromptEnvelope:
    system_rules: tuple[str, ...]
    user_query: str
    evidence_blocks: tuple[dict[str, Any], ...]
    contradiction_blocks: tuple[dict[str, Any], ...]
    required_output_contract: dict[str, Any]
