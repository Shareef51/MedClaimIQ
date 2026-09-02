from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class SurveillanceSignalRequest(BaseModel):
    intervention_program_id: str
    closure_systemic_risk_score: float = 0
    current_systemic_risk_score: float = 0
    systemic_risk_rebound_threshold: float = 15
    control_effectiveness_decay_percent: float = 0
    control_decay_threshold_percent: float = 20
    new_recurrence_count: int = 0
    regulator_followup_reopened: bool = False

class ExaminationCorrelationRequest(BaseModel):
    intervention_program_id: str
    examination_id: str
    obligation_overlap: float = 0
    control_overlap: float = 0
    root_cause_similarity: float = 0
    entity_overlap: float = 0
    match_threshold: float = 0.65

class RecurrenceInvestigationRequest(BaseModel):
    intervention_program_id: str
    finding_ids: list[str] = Field(default_factory=list)
    affected_entity_ids: list[str] = Field(default_factory=list)
    program_entity_ids: list[str] = Field(default_factory=list)
    root_cause_comparison: dict[str, Any] = Field(default_factory=dict)
    prior_closure_version_id: str
    prior_residual_risk_acceptance_version_id: str
    regulator_followup_refs: list[str] = Field(default_factory=list)
    renewed_action_plan_refs: list[str] = Field(default_factory=list)
    rationale: str

class IndependentReassessmentRequest(BaseModel):
    intervention_program_id: str
    investigation_version_id: str
    reviewer_role: str
    effectiveness_reconfirmed: bool
    residual_systemic_risk_score: float
    evidence_refs: list[str] = Field(default_factory=list)
    rationale: str

class ReopeningReadinessRequest(BaseModel):
    intervention_program_id: str
    investigation_complete: bool
    independent_reassessment_complete: bool
    executive_review_complete: bool
    internal_audit_review_complete: bool
    renewed_remediation_candidate_defined: bool

class ProgramReopeningDecisionRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    decision: str
    reopening_readiness_score: float
    investigation_version_id: str
    independent_reassessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
