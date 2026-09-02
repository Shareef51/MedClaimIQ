from typing import Any
from pydantic import BaseModel, Field


class ReopenedOutcomeRequest(BaseModel):
    deficiency_key: str
    reopen_investigation_id: str
    renewed_remediation_refs: list[dict[str, Any]] = Field(min_length=1)
    corrective_action_refs: list[dict[str, Any]] = Field(min_length=1)
    milestone_refs: list[dict[str, Any]] = Field(default_factory=list)
    prior_root_cause_refs: list[dict[str, Any]] = Field(default_factory=list)
    current_root_cause_refs: list[dict[str, Any]] = Field(default_factory=list)
    cross_entity_scope: list[str] = Field(default_factory=list)
    renewed_commitment_refs: list[dict[str, Any]] = Field(default_factory=list)


class IndependentRevalidationRequest(BaseModel):
    deficiency_key: str
    outcome_id: str
    control_ref: dict[str, Any]
    prior_effectiveness_score: float = Field(ge=0, le=1)
    current_effectiveness_score: float = Field(ge=0, le=1)
    recurrence_containment_score: float = Field(ge=0, le=1)
    retest_evidence_refs: list[dict[str, Any]] = Field(min_length=1)
    independent_evidence_refs: list[dict[str, Any]] = Field(min_length=1)
    cross_entity_validation_refs: list[dict[str, Any]] = Field(default_factory=list)


class ClosureAssuranceRequest(BaseModel):
    deficiency_key: str
    outcome_id: str
    revalidation_refs: list[dict[str, Any]] = Field(min_length=1)
    sustainability_window_days: int = Field(default=90, ge=30, le=730)
    sustainability_evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    current_effectiveness_score: float = Field(ge=0, le=1)
    recurrence_containment_score: float = Field(ge=0, le=1)
    independent_validated: bool
    sustainability_complete: bool
    cross_entity_complete: bool
    commitments_complete: bool
    second_recurrence_count: int = Field(default=0, ge=0)


class HumanRecertificationRequest(BaseModel):
    decision: str = Field(pattern="^(reclose|monitor|extend_remediation)$")
    rationale: str = Field(min_length=30)
    certification_refs: list[dict[str, Any]] = Field(default_factory=list)
