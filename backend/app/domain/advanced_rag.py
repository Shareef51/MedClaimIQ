from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.orchestration import AgentName
from app.domain.rag import QueryPlan, RAGDomain, RetrievalAssessment, RetrievalHit, RetrievalStrategy


class QueryIntent(StrEnum):
    EXACT_CODE = "exact_code"
    POLICY_INTERPRETATION = "policy_interpretation"
    TEMPORAL_VERIFICATION = "temporal_verification"
    CROSS_SOURCE_VERIFICATION = "cross_source_verification"
    DUPLICATE_SEARCH = "duplicate_search"
    FACT_LOOKUP = "fact_lookup"
    BROAD_INVESTIGATION = "broad_investigation"


class RoutingMode(StrEnum):
    EXACT = "exact"
    DENSE_SEMANTIC = "dense_semantic"
    HYBRID_BALANCED = "hybrid_balanced"
    HYBRID_HYDE = "hybrid_hyde"


class Answerability(StrEnum):
    ANSWERABLE = "answerable"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class GapSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class MetadataOperator(StrEnum):
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"
    IN = "in"


@dataclass(frozen=True, slots=True)
class MetadataPredicate:
    field: str
    operator: MetadataOperator
    value: Any
    source: str = "deterministic_self_query"


@dataclass(frozen=True, slots=True)
class AdaptiveRoute:
    mode: RoutingMode
    strategy: RetrievalStrategy
    use_hyde: bool
    candidate_multiplier: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentRetrievalDirective:
    agent: AgentName | None
    domains: tuple[RAGDomain, ...]
    required_evidence_types: tuple[str, ...]
    minimum_authority_rank: int
    max_rounds: int
    require_citations: bool = True
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AdvancedQueryPlan:
    query_plan: QueryPlan
    intent: QueryIntent
    rewrites: tuple[str, ...]
    hypothetical_document: str | None
    metadata_predicates: tuple[MetadataPredicate, ...]
    route: AdaptiveRoute
    agent_directive: AgentRetrievalDirective
    planner_version: str
    model_assisted: bool = False
    transformation_hashes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CitationCheck:
    chunk_id: str
    valid: bool
    reasons: tuple[str, ...]
    source_id: str | None
    source_version: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeGap:
    code: str
    severity: GapSeverity
    description: str
    domain: RAGDomain | None = None
    recommended_action: str = "retrieve_more"


@dataclass(frozen=True, slots=True)
class AdvancedRAGResult:
    advanced_run_id: str
    retrieval_run_id: str
    query: str
    plan: AdvancedQueryPlan
    hits: tuple[RetrievalHit, ...]
    assessment: RetrievalAssessment
    citations: tuple[CitationCheck, ...]
    citation_coverage: float
    knowledge_gaps: tuple[KnowledgeGap, ...]
    answerability: Answerability
    rounds_executed: int
    fallback_steps: tuple[str, ...]
    latency_ms: int
    trace_id: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
