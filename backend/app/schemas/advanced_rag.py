from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.advanced_rag import Answerability, GapSeverity, QueryIntent, RoutingMode
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain, RetrievalStrategy


class AdvancedRAGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=4000)
    agent: AgentName | None = None
    domains: tuple[RAGDomain, ...] = ()
    entity_ids: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    top_k: int = Field(default=8, ge=1, le=20)
    minimum_authority_rank: int = Field(default=0, ge=0, le=100)
    service_date_from: date | None = None
    service_date_to: date | None = None
    enable_hyde: bool = True
    enable_model_assisted_rewriting: bool = False
    strict_citations: bool = True

    @field_validator("source_types")
    @classmethod
    def validate_source_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(dict.fromkeys(item.strip().lower() for item in value if item.strip()))
        if any(len(item) > 80 or not all(ch.isalnum() or ch in "_-" for ch in item) for item in cleaned):
            raise ValueError("source_types must contain only safe source-type identifiers")
        return cleaned


class MetadataPredicateResponse(BaseModel):
    field: str
    operator: str
    value: object
    source: str


class AdvancedPlanResponse(BaseModel):
    query: str
    intent: QueryIntent
    normalized_query: str
    rewrites: list[str]
    hypothetical_document: str | None = None
    metadata_predicates: list[MetadataPredicateResponse]
    routing_mode: RoutingMode
    strategy: RetrievalStrategy
    use_hyde: bool
    planned_domains: list[RAGDomain]
    minimum_authority_rank: int
    service_date_from: date | None = None
    service_date_to: date | None = None
    agent: AgentName | None = None
    required_evidence_types: list[str]
    max_rounds: int
    planner_version: str
    model_assisted: bool


class AdvancedRAGHitResponse(BaseModel):
    chunk_id: str
    domain: RAGDomain
    score: float
    rerank_score: float | None = None
    text: str
    citation: dict[str, object]
    metadata: dict[str, object]
    retrieval_sources: list[str]


class CitationCheckResponse(BaseModel):
    chunk_id: str
    valid: bool
    reasons: list[str]
    source_id: str | None = None
    source_version: str | None = None


class KnowledgeGapResponse(BaseModel):
    code: str
    severity: GapSeverity
    description: str
    domain: RAGDomain | None = None
    recommended_action: str


class AdvancedRAGResponse(BaseModel):
    claim_id: str
    advanced_run_id: str
    retrieval_run_id: str
    plan: AdvancedPlanResponse
    answerability: Answerability
    confidence: float
    coverage: float
    source_diversity: float
    citation_coverage: float
    rounds_executed: int
    latency_ms: int
    fallback_steps: list[str]
    knowledge_gaps: list[KnowledgeGapResponse]
    citation_checks: list[CitationCheckResponse]
    hits: list[AdvancedRAGHitResponse]


class AdvancedRAGRunSummary(BaseModel):
    advanced_run_id: str
    retrieval_run_id: str
    agent_name: str | None = None
    query_intent: str
    routing_mode: str
    retrieval_strategy: str
    confidence: float
    citation_coverage: float
    answerability: str
    knowledge_gap_count: int
    latency_ms: int
    created_at: datetime
