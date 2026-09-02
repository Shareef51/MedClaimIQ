from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, Iterable


class RAGDomain(StrEnum):
    CLAIM = "claim"
    POLICY = "policy"
    HOSPITAL = "hospital"
    INVOICE = "invoice"
    CODING = "coding"
    HISTORICAL_CLAIMS = "historical_claims"
    EVIDENCE = "evidence"


class ChunkKind(StrEnum):
    PARENT = "parent"
    CHILD = "child"
    TABLE = "table"
    TRANSCRIPT = "transcript"


class IndexAction(StrEnum):
    INDEX = "index"
    REINDEX = "reindex"
    DELETE = "delete"


class RetrievalStrategy(StrEnum):
    HYBRID = "hybrid"
    DENSE = "dense"
    SPARSE = "sparse"


class IndexJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class CitationAnchor:
    evidence_id: str | None = None
    extraction_unit_id: str | None = None
    page_number: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    bbox: tuple[float, ...] | None = None
    frame_index: int | None = None
    frame_sha256: str | None = None
    source_locator: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "extraction_unit_id": self.extraction_unit_id,
            "page_number": self.page_number,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "bbox": list(self.bbox) if self.bbox else None,
            "frame_index": self.frame_index,
            "frame_sha256": self.frame_sha256,
            "source_locator": self.source_locator,
        }


@dataclass(frozen=True)
class SourceSegment:
    segment_id: str
    text: str
    unit_type: str = "text"
    citation: CitationAnchor | None = None
    structured_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeDocument:
    tenant_id: str
    claim_id: str
    patient_subject_id: str
    domain: RAGDomain
    source_type: str
    source_id: str
    source_version: str
    source_content_sha256: str | None
    segments: tuple[SourceSegment, ...]
    authority_rank: int
    evidence_confidence: float
    entity_ids: tuple[str, ...] = ()
    relationship_types: tuple[str, ...] = ()
    acl_tags: tuple[str, ...] = ("claim_authorized",)
    service_date: date | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RAGChunk:
    chunk_id: str
    tenant_id: str
    claim_id: str
    patient_subject_id: str
    domain: RAGDomain
    source_type: str
    source_id: str
    source_version: str
    parent_chunk_id: str | None
    kind: ChunkKind
    ordinal: int
    text: str
    content_sha256: str
    token_count: int
    citation: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievalScope:
    tenant_id: str
    claim_id: str | None = None
    patient_subject_id: str | None = None
    domains: tuple[RAGDomain, ...] = ()
    acl_tags: tuple[str, ...] = ("claim_authorized",)
    entity_ids: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    service_date_from: date | None = None
    service_date_to: date | None = None
    minimum_authority_rank: int = 0


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    normalized_query: str
    variants: tuple[str, ...]
    subqueries: tuple[str, ...]
    domains: tuple[RAGDomain, ...]
    exact_terms: tuple[str, ...] = ()
    service_date_from: date | None = None
    service_date_to: date | None = None
    minimum_authority_rank: int = 0
    planner_version: str = ""
    fallbacks: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalAssessment:
    confidence: float
    coverage: float
    source_diversity: float
    no_evidence: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    domain: RAGDomain
    score: float
    text: str
    parent_chunk_id: str | None
    citation: dict[str, Any]
    metadata: dict[str, Any]
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    query_variant: str | None = None
    retrieval_sources: tuple[str, ...] = ()


def rag_domains() -> tuple[str, ...]:
    return tuple(item.value for item in RAGDomain)


def sanitize_acl_tags(tags: Iterable[str]) -> tuple[str, ...]:
    normalized = sorted({tag.strip().lower() for tag in tags if tag and tag.strip()})
    return tuple(normalized)
