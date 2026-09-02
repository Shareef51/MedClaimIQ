from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

KnowledgeClass = Literal["authoritative", "approved_internal", "advisory", "historical", "superseded"]

class KnowledgeNodeRequest(BaseModel):
    node_type: str
    canonical_key: str
    title: str
    knowledge_class: KnowledgeClass = "advisory"
    effective_at: str
    expires_at: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    entity_scope: list[str] = Field(default_factory=list)

class KnowledgeEdgeRequest(BaseModel):
    source_key: str
    target_key: str
    edge_type: str
    evidence_refs: list[str] = Field(default_factory=list)

class ExaminationQueryRequest(BaseModel):
    question: str
    as_of: str
    entity_ids: list[str] = Field(default_factory=list)
    regulator: str | None = None

class KnowledgeApprovalRequest(BaseModel):
    decision: Literal["approve", "reject", "supersede"]
    rationale: str = Field(min_length=8)
    expected_version: int = Field(ge=1)

class ReadinessAssessmentRequest(BaseModel):
    examination_id: str
    authoritative_coverage: float = Field(ge=0, le=1)
    evidence_freshness: float = Field(ge=0, le=1)
    control_lineage_coverage: float = Field(ge=0, le=1)
    open_conflict_resolution: float = Field(ge=0, le=1)
    historical_finding_coverage: float = Field(ge=0, le=1)
