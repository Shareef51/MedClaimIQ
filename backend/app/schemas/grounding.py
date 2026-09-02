from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.domain.cross_source_rag import RetrieverKind
from app.domain.rag import RAGDomain
from app.domain.grounding import CitationStatus, GuardrailDecision, InjectionRisk, StatementSupport


class CandidateCitationRequest(BaseModel):
    evidence_key: str = Field(min_length=1, max_length=128)
    source_id: str | None = Field(default=None, max_length=256)
    source_version: str | None = Field(default=None, max_length=128)
    locator: dict[str, Any] = Field(default_factory=dict)


class CandidateStatementRequest(BaseModel):
    statement_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    citations: list[CandidateCitationRequest] = Field(default_factory=list, max_length=12)


class GroundingCheckRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    retrievers: tuple[RetrieverKind, ...] = ()
    domains: tuple[RAGDomain, ...] = ()
    entity_ids: tuple[str, ...] = ()
    service_date_from: date | None = None
    service_date_to: date | None = None
    minimum_authority_rank: int = Field(default=0, ge=0, le=100)
    top_k: int = Field(default=12, ge=1, le=30)
    graph_max_depth: int = Field(default=2, ge=1, le=4)
    max_repairs: int = Field(default=2, ge=0, le=2)
    candidate_statements: list[CandidateStatementRequest] = Field(default_factory=list, max_length=40)


class InjectionFindingResponse(BaseModel):
    evidence_key: str
    risk: InjectionRisk
    score: float
    rule_ids: list[str]
    action: str


class EvidenceQualityResponse(BaseModel):
    score: float
    qualifying_evidence_count: int
    authoritative_evidence_count: int
    source_type_count: int
    excluded_injection_count: int
    unresolved_material_contradictions: int
    reasons: list[str]


class AnswerabilityResponse(BaseModel):
    answerable: bool
    score: float
    reasons: list[str]
    requires_repair: bool
    requires_human_review: bool


class StatementGroundingResponse(BaseModel):
    statement_id: str
    support: StatementSupport
    support_score: float
    citation_status: CitationStatus
    verified_evidence_keys: list[str]
    invalid_evidence_keys: list[str]
    numeric_integrity: bool
    medical_code_integrity: bool
    contradiction_safe: bool
    reasons: list[str]


class RepairAttemptResponse(BaseModel):
    attempt_number: int
    strategy: str
    requested_retrievers: list[str]
    result_pack_id: str | None
    confidence: float
    answerable: bool


class SafeEvidenceResponse(BaseModel):
    evidence_key: str
    source_type: str
    source_id: str
    source_version: str | None
    text: str
    authority_rank: int
    confidence: float
    citation: dict[str, Any]


class GroundingCheckResponse(BaseModel):
    run_id: str
    claim_id: str
    pack_id: str
    decision: GuardrailDecision
    guardrail_version: str
    evidence_quality: EvidenceQualityResponse
    answerability: AnswerabilityResponse
    injection_findings: list[InjectionFindingResponse]
    safe_evidence: list[SafeEvidenceResponse]
    statement_checks: list[StatementGroundingResponse]
    repair_attempts: list[RepairAttemptResponse]
    escalation_reasons: list[str]
    generation_contract: dict[str, Any]
