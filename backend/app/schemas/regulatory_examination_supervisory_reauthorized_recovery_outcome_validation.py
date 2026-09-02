from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class SupervisoryRecoveryOutcomeRequest(BaseModel):
    recovery_program_id: str
    release92_supervisory_recovery_execution_version_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)

class SupervisorySystemicRiskReductionRequest(BaseModel):
    recovery_program_id: str
    release92_baseline_systemic_risk_score: float
    current_systemic_risk_score: float
    minimum_required_reduction_percent: float = 35.0

class SupervisoryCrossEntityCompletionRequest(BaseModel):
    recovery_program_id: str
    entities: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryRepeatedFailureControlEffectivenessRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryIndependentOutcomeAssuranceRequest(BaseModel):
    recovery_program_id: str
    release92_supervisory_recovery_execution_version_id: str
    release92_independent_recovery_assurance_version_id: str
    reviewer_role: str
    tests: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = "pending"
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisoryRegulatoryCommitmentCompletionRequest(BaseModel):
    recovery_program_id: str
    commitments: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryBlockerGovernanceRequest(BaseModel):
    recovery_program_id: str
    blockers: list[dict[str, Any]] = Field(default_factory=list)

class SupervisorySustainabilityWindowRequest(BaseModel):
    recovery_program_id: str
    observed_window_days: int = 0
    minimum_window_days: int = 90
    minimum_control_health_score: float = 88.0
    observations: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryReclosureReadinessRequest(BaseModel):
    recovery_program_id: str
    release92_supervisory_execution_reference_present: bool = False
    release92_independent_assurance_reference_present: bool = False
    supervisory_recovery_outcomes_complete: bool = False
    cross_entity_retransformation_completion_reconciled: bool = False
    repeated_failure_controls_effective: bool = False
    independent_recovery_outcome_validated: bool = False
    systemic_risk_reduction_verified: bool = False
    unresolved_blockers_cleared: bool = False
    regulatory_commitments_reconciled: bool = False
    sustainability_window_passed: bool = False
    residual_risk_human_decision_recorded: bool = False

class SupervisoryResidualRiskReassessmentRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    residual_systemic_risk_score: float
    release92_supervisory_recovery_execution_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisoryRecoveryRecertificationRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    release92_supervisory_recovery_execution_version_id: str
    release92_independent_recovery_assurance_version_id: str
    independent_outcome_validation_version_id: str
    residual_risk_decision_version_id: str
    sustainability_assessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisorySustainabilityReclosureRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    recovery_recertification_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
