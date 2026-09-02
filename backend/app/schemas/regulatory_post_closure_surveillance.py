from typing import Any
from pydantic import BaseModel, Field

class SurveillanceSignalRequest(BaseModel):
    deficiency_key: str
    signal_type: str = Field(pattern="^(new_exam_match|control_regression|recurrence|sustainability_decay|regulator_followup)$")
    source_ref: dict[str,Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str,Any]] = Field(min_length=1)
    recurrence_score: float = Field(ge=0,le=1)
    sustainability_decay_score: float = Field(ge=0,le=1)
    control_regression_score: float = Field(ge=0,le=1)
    cross_entity_keys: list[str] = Field(default_factory=list)

class ReopenCandidateRequest(BaseModel):
    deficiency_key: str
    trigger: str = Field(min_length=5,max_length=80)
    matched_closed_finding_refs: list[dict[str,Any]] = Field(min_length=1)
    prior_certification_refs: list[dict[str,Any]] = Field(default_factory=list)
    recurrence_evidence_refs: list[dict[str,Any]] = Field(min_length=1)
    renewed_corrective_action_refs: list[dict[str,Any]] = Field(default_factory=list)
    regulator_followup_refs: list[dict[str,Any]] = Field(default_factory=list)
    recommended_action: str = Field(pattern="^(monitor|investigate|reopen_candidate)$")

class HumanReopenDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(reopen|keep_closed|monitor)$")
    rationale: str = Field(min_length=30)
    renewed_corrective_action_refs: list[dict[str,Any]] = Field(default_factory=list)
