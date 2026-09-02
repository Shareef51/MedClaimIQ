from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.rag import RAGDomain, RetrievalStrategy


class DenseSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=4000)
    domains: tuple[RAGDomain, ...] = ()
    entity_ids: tuple[str, ...] = ()
    top_k: int = Field(default=8, ge=1, le=20)
    hydrate_parent: bool = True


class DenseSearchHit(BaseModel):
    chunk_id: str
    domain: RAGDomain
    score: float
    text: str
    parent_chunk_id: str | None = None
    citation: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class DenseSearchResponse(BaseModel):
    claim_id: str
    query: str
    hits: list[DenseSearchHit]


class HybridSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=4000)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    domains: tuple[RAGDomain, ...] = ()
    entity_ids: tuple[str, ...] = ()
    top_k: int = Field(default=8, ge=1, le=20)
    hydrate_parent: bool = True
    compress_context: bool = True
    minimum_authority_rank: int = Field(default=0, ge=0, le=100)
    service_date_from: date | None = None
    service_date_to: date | None = None


class QueryPlanResponse(BaseModel):
    normalized_query: str
    variants: list[str]
    subqueries: list[str]
    domains: list[RAGDomain]
    exact_terms: list[str]
    service_date_from: date | None = None
    service_date_to: date | None = None
    minimum_authority_rank: int
    planner_version: str
    fallbacks: list[str]


class HybridSearchHit(BaseModel):
    chunk_id: str
    domain: RAGDomain
    score: float
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    text: str
    parent_chunk_id: str | None = None
    citation: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    retrieval_sources: list[str] = Field(default_factory=list)


class RetrievalAssessmentResponse(BaseModel):
    confidence: float
    coverage: float
    source_diversity: float
    no_evidence: bool
    reasons: list[str]


class HybridSearchResponse(BaseModel):
    claim_id: str
    retrieval_run_id: str
    query: str
    strategy: RetrievalStrategy
    plan: QueryPlanResponse
    assessment: RetrievalAssessmentResponse
    fallback_steps: list[str]
    latency_ms: int
    hits: list[HybridSearchHit]
