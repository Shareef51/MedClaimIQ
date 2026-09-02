from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.advanced_rag import Answerability
from app.domain.multimodal_rag import EvidenceModality, InconsistencySeverity, MultimodalIntent
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain


class MultimodalRAGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=4000)
    agent: AgentName | None = None
    domains: tuple[RAGDomain, ...] = ()
    modalities: tuple[EvidenceModality, ...] = ()
    required_modalities: tuple[EvidenceModality, ...] = ()
    top_k: int = Field(default=12, ge=1, le=30)
    minimum_authority_rank: int = Field(default=0, ge=0, le=100)

    @field_validator("required_modalities")
    @classmethod
    def required_must_be_requested_when_explicit(cls, value, info):
        requested = set(info.data.get("modalities") or ())
        if requested and not set(value).issubset(requested):
            raise ValueError("required_modalities must be a subset of modalities when modalities are explicitly provided")
        return tuple(dict.fromkeys(value))


class MultimodalPlanResponse(BaseModel):
    query: str
    intent: MultimodalIntent
    modalities: list[EvidenceModality]
    required_modalities: list[EvidenceModality]
    agent: AgentName | None = None
    reasons: list[str]
    planner_version: str


class MultimodalCitationResponse(BaseModel):
    modality: EvidenceModality
    evidence_id: str | None = None
    extraction_unit_id: str | None = None
    page_number: int | None = None
    bbox: list[float] | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    frame_index: int | None = None
    frame_sha256: str | None = None
    fhir_snapshot_id: str | None = None
    fhir_resource_type: str | None = None
    fhir_logical_id: str | None = None
    fhir_version_id: str | None = None
    source_locator: dict[str, object]


class MultimodalItemResponse(BaseModel):
    item_id: str
    modality: EvidenceModality
    domain: RAGDomain
    source_id: str
    source_version: str
    text: str
    score: float
    confidence: float
    authority_rank: int
    citation: MultimodalCitationResponse
    metadata: dict[str, object]
    retrieval_sources: list[str]


class MultimodalInconsistencyResponse(BaseModel):
    code: str
    field: str
    severity: InconsistencySeverity
    left_item_id: str
    right_item_id: str
    left_value: str
    right_value: str
    confidence: float
    description: str


class MultimodalGapResponse(BaseModel):
    code: str
    description: str
    blocking: bool
    modality: EvidenceModality | None = None


class MultimodalRAGResponse(BaseModel):
    claim_id: str
    run_id: str
    pack_id: str
    plan: MultimodalPlanResponse
    answerability: Answerability
    confidence: float
    modality_coverage: float
    citation_coverage: float
    source_diversity: float
    latency_ms: int
    items: list[MultimodalItemResponse]
    inconsistencies: list[MultimodalInconsistencyResponse]
    gaps: list[MultimodalGapResponse]
    diagnostics: dict[str, object]


class MultimodalRunSummary(BaseModel):
    run_id: str
    intent: str
    routed_modalities: list[str]
    selected_count: int
    confidence: float
    modality_coverage: float
    citation_coverage: float
    inconsistency_count: int
    answerability: str
    latency_ms: int
    created_at: datetime
