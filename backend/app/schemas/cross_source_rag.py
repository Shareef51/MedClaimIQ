from __future__ import annotations

from datetime import date
from pydantic import BaseModel, ConfigDict, Field

from app.domain.cross_source_rag import RetrieverKind
from app.domain.rag import RAGDomain


class EvidenceSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=4000)
    retrievers: tuple[RetrieverKind, ...] = ()
    domains: tuple[RAGDomain, ...] = ()
    entity_ids: tuple[str, ...] = ()
    top_k: int = Field(default=12, ge=1, le=30)
    graph_max_depth: int = Field(default=2, ge=1, le=4)
    minimum_authority_rank: int = Field(default=0, ge=0, le=100)
    service_date_from: date | None = None
    service_date_to: date | None = None


class UnifiedCitationResponse(BaseModel):
    source_type: str
    source_id: str
    source_version: str | None = None
    locator: dict[str, object] = Field(default_factory=dict)
    entity_ids: list[str] = Field(default_factory=list)
    relationship_path: list[str] = Field(default_factory=list)


class EvidenceItemResponse(BaseModel):
    evidence_key: str
    retriever: RetrieverKind
    source_type: str
    source_id: str
    source_version: str | None = None
    text: str
    authority_rank: int
    confidence: float
    citation: UnifiedCitationResponse
    metadata: dict[str, object] = Field(default_factory=dict)


class ContradictionResponse(BaseModel):
    contradiction_id: str
    field_name: str
    severity: str
    confidence: float
    left_value: object
    right_value: object
    status: str


class EvidencePackAssessmentResponse(BaseModel):
    confidence: float
    coverage: float
    source_diversity: float
    no_evidence: bool
    unresolved_material_contradictions: int
    reasons: list[str]


class EvidencePackResponse(BaseModel):
    claim_id: str
    pack_id: str
    query: str
    requested_retrievers: list[RetrieverKind]
    executed_retrievers: list[RetrieverKind]
    planner_version: str
    assessment: EvidencePackAssessmentResponse
    evidence: list[EvidenceItemResponse]
    contradictions: list[ContradictionResponse]
