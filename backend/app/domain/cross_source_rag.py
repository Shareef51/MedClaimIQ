from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Any, Iterable


class RetrieverKind(StrEnum):
    VECTOR = "vector"
    SQL = "sql"
    FHIR = "fhir"
    GRAPH = "graph"


class StructuredFact(StrEnum):
    CLAIM = "claim"
    CLAIM_LINES = "claim_lines"
    POLICY = "policy"
    ENCOUNTER = "encounter"
    PROVIDER = "provider"
    CONTRADICTIONS = "contradictions"


@dataclass(frozen=True, slots=True)
class StructuredQueryPlan:
    facts: tuple[StructuredFact, ...]
    claim_id: str
    service_date_from: date | None = None
    service_date_to: date | None = None
    max_rows: int = 50

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id is required")
        if self.max_rows < 1 or self.max_rows > 200:
            raise ValueError("max_rows must be between 1 and 200")
        if self.service_date_from and self.service_date_to and self.service_date_to < self.service_date_from:
            raise ValueError("service_date_to must be on or after service_date_from")


@dataclass(frozen=True, slots=True)
class FHIRQueryPlan:
    claim_id: str
    resource_types: tuple[str, ...] = (
        "Patient", "Encounter", "Coverage", "Claim", "ExplanationOfBenefit", "DocumentReference",
    )
    max_resources: int = 50

    def __post_init__(self) -> None:
        allowed = {"Patient", "Encounter", "Coverage", "Claim", "ExplanationOfBenefit", "DocumentReference", "Organization", "Practitioner"}
        if not self.claim_id:
            raise ValueError("claim_id is required")
        if not set(self.resource_types).issubset(allowed):
            raise ValueError("unsupported FHIR resource type")
        if self.max_resources < 1 or self.max_resources > 200:
            raise ValueError("max_resources must be between 1 and 200")


@dataclass(frozen=True, slots=True)
class GraphQueryPlan:
    claim_id: str
    start_entity_ids: tuple[str, ...] = ()
    relationship_types: tuple[str, ...] = ()
    max_depth: int = 2
    max_edges: int = 60
    as_of: date | None = None

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id is required")
        if self.max_depth < 1 or self.max_depth > 4:
            raise ValueError("max_depth must be between 1 and 4")
        if self.max_edges < 1 or self.max_edges > 200:
            raise ValueError("max_edges must be between 1 and 200")


@dataclass(frozen=True, slots=True)
class UnifiedCitation:
    source_type: str
    source_id: str
    source_version: str | None = None
    locator: dict[str, Any] = field(default_factory=dict)
    entity_ids: tuple[str, ...] = ()
    relationship_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_key: str
    retriever: RetrieverKind
    source_type: str
    source_id: str
    text: str
    authority_rank: int
    confidence: float
    citation: UnifiedCitation
    source_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_sha256(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ContradictionSummary:
    contradiction_id: str
    field_name: str
    severity: str
    confidence: float
    left_value: Any
    right_value: Any
    status: str


@dataclass(frozen=True, slots=True)
class EvidencePackAssessment:
    confidence: float
    coverage: float
    source_diversity: float
    no_evidence: bool
    unresolved_material_contradictions: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidencePack:
    pack_id: str
    claim_id: str
    query: str
    items: tuple[EvidenceItem, ...]
    contradictions: tuple[ContradictionSummary, ...]
    assessment: EvidencePackAssessment
    executed_retrievers: tuple[RetrieverKind, ...]
    planner_version: str


def evidence_key(*parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    return f"evi_{sha256(material.encode()).hexdigest()[:32]}"


def deduplicate_evidence(items: Iterable[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    by_key: dict[str, EvidenceItem] = {}
    for item in items:
        current = by_key.get(item.evidence_key)
        if current is None or (item.authority_rank, item.confidence) > (current.authority_rank, current.confidence):
            by_key[item.evidence_key] = item
    return tuple(by_key.values())
