from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RenewedRecoveryOutcomeRequest(BaseModel):
    intervention_program_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)


class SystemicRiskReductionRequest(BaseModel):
    intervention_program_id: str
    baseline_systemic_risk_score: float
    current_systemic_risk_score: float
    minimum_required_reduction_percent: float = 25.0


class CrossEntityCompletionRequest(BaseModel):
    intervention_program_id: str
    entities: list[dict[str, Any]] = Field(default_factory=list)


class IndependentRecoveryEffectivenessRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    tests: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = "pending"
    evidence_refs: list[str] = Field(default_factory=list)


class RegulatoryCommitmentCompletionRequest(BaseModel):
    intervention_program_id: str
    commitments: list[dict[str, Any]] = Field(default_factory=list)


class SustainabilityWindowRequest(BaseModel):
    intervention_program_id: str
    observed_window_days: int = 0
    minimum_window_days: int = 30
    minimum_control_health_score: float = 80.0
    observations: list[dict[str, Any]] = Field(default_factory=list)


class ReclosureReadinessRequest(BaseModel):
    intervention_program_id: str
    renewed_recovery_outcomes_complete: bool = False
    cross_entity_completion_reconciled: bool = False
    independent_recovery_effectiveness_validated: bool = False
    systemic_risk_reduction_verified: bool = False
    unresolved_blockers_cleared: bool = False
    regulatory_commitments_reconciled: bool = False
    sustainability_window_passed: bool = False
    residual_risk_human_decision_recorded: bool = False


class ResidualRiskReassessmentRequest(BaseModel):
    intervention_program_id: str
    actor_role: str
    decision: str
    residual_systemic_risk_score: float
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class RecoveryRecertificationRequest(BaseModel):
    intervention_program_id: str
    actor_role: str
    decision: str
    independent_validation_version_id: str
    residual_risk_decision_version_id: str
    sustainability_assessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class SustainabilityReclosureRequest(BaseModel):
    intervention_program_id: str
    actor_role: str
    decision: str
    recovery_recertification_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
