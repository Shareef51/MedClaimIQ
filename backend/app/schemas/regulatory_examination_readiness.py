from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class ExaminationScopeRequest(BaseModel):
    examination_id: str
    regulator: str
    legal_entity_ids: list[str] = Field(min_length=1)
    scope_topics: list[str] = Field(min_length=1)
    start_at: datetime
    target_end_at: datetime | None = None
    owner_id: str

class RegulatorRequestCreate(BaseModel):
    examination_id: str
    external_request_ref: str
    request_text: str
    due_at: datetime
    owner_id: str
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    requested_artifact_types: list[str] = []

class EvidenceMapRequest(BaseModel):
    request_id: str
    evidence_id: str
    evidence_class: Literal["standard", "confidential", "restricted", "regulatory_privileged", "legal_privileged"]
    source_system: str
    version_id: str
    content_hash: str
    citation_anchor: str
    approved_for_exam_use: bool = False

class ResponseDraftRequest(BaseModel):
    request_id: str
    answer: str
    citation_ids: list[str] = Field(min_length=1)
    generated_by: Literal["human", "ai_assisted"] = "ai_assisted"

class HumanResponseDecision(BaseModel):
    decision: Literal["approve", "reject", "return_for_changes"]
    rationale: str = Field(min_length=3)
    expected_version: int = Field(ge=1)

class EvidenceRoomPackageRequest(BaseModel):
    examination_id: str
    request_ids: list[str] = Field(min_length=1)
    package_name: str

class SubmissionPackageDecision(BaseModel):
    decision: Literal["approve", "reject"]
    rationale: str = Field(min_length=3)
    expected_version: int = Field(ge=1)

class ReadinessAssessmentRequest(BaseModel):
    examination_id: str
    request_coverage: float = Field(ge=0, le=1)
    evidence_completeness: float = Field(ge=0, le=1)
    citation_validation: float = Field(ge=0, le=1)
    conflict_resolution: float = Field(ge=0, le=1)
    privileged_segregation: float = Field(ge=0, le=1)
    owner_assignment: float = Field(ge=0, le=1)
    deadline_health: float = Field(ge=0, le=1)
