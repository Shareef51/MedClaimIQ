from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class RiskReductionAssessmentRequest(BaseModel):
    intervention_program_id: str
    baseline_systemic_risk_score: float
    post_remediation_systemic_risk_score: float
    minimum_reduction_percent: float = 50

class SustainabilityAssuranceRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    required_entity_ids: list[str] = Field(default_factory=list)
    sustainability_observations: list[dict[str, Any]] = Field(default_factory=list)
    sustainability_window_complete: bool = False
    rationale: str

class ResidualRiskAcceptanceRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    decision: str
    residual_systemic_risk_score: float
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class ClosureReadinessRequest(BaseModel):
    intervention_program_id: str
    implementation_complete: bool
    independent_effectiveness_passed: bool
    sustainability_assurance_passed: bool
    cross_entity_reconciled: bool
    regulatory_commitments_reconciled: bool
    unresolved_blocker_count: int = 0
    residual_risk_accepted_by_human: bool = False

class ExecutiveProgramClosureRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    decision: str
    rationale: str
    residual_risk_acceptance_version_id: str
    sustainability_assurance_version_id: str
    closure_readiness_score: float
    evidence_refs: list[str] = Field(default_factory=list)

class RecurrenceReopenSignalRequest(BaseModel):
    intervention_program_id: str
    recurrence_detected: bool = False
    control_health_decay_percent: float = 0
    control_health_decay_threshold_percent: float = 20
    regulator_followup_reopened: bool = False
