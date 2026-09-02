from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class EnterpriseRecoveryOutcomeRequest(BaseModel):
    recovery_program_id: str
    release100_enterprise_remediation_execution_version_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)


class RootCauseTreatmentEffectivenessRequest(BaseModel):
    recovery_program_id: str
    treatments: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseSystemicRiskReductionRequest(BaseModel):
    recovery_program_id: str
    release100_baseline_systemic_risk_score: float
    current_systemic_risk_score: float
    minimum_required_reduction_percent: float = 40.0

class EnterpriseControlCompletionRequest(BaseModel):
    recovery_program_id: str
    entities: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseRepeatedFailureControlEffectivenessRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseIndependentOutcomeAssuranceRequest(BaseModel):
    recovery_program_id: str
    release100_enterprise_remediation_execution_version_id: str
    release100_independent_recovery_effectiveness_assurance_version_id: str
    reviewer_role: str
    implementation_owner_id: str | None = None
    tests: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = "pending"
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRegulatoryCommitmentCompletionRequest(BaseModel):
    recovery_program_id: str
    commitments: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseBlockerGovernanceRequest(BaseModel):
    recovery_program_id: str
    blockers: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseControlHealthRequest(BaseModel):
    recovery_program_id: str
    minimum_control_health_score: float = 90.0
    entities: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseSustainabilityWindowRequest(BaseModel):
    recovery_program_id: str
    observed_window_days: int = 0
    minimum_window_days: int = 180
    minimum_control_health_score: float = 90.0
    observations: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseReclosureReadinessRequest(BaseModel):
    recovery_program_id: str
    release100_enterprise_remediation_execution_reference_present: bool = False
    release100_independent_recovery_effectiveness_assurance_reference_present: bool = False
    enterprise_recovery_outcomes_complete: bool = False
    persistent_emergent_root_cause_treatments_effective: bool = False
    enterprise_control_retransformation_completion_reconciled: bool = False
    repeated_failure_controls_effective: bool = False
    independent_enterprise_recovery_outcome_validated: bool = False
    systemic_risk_reduction_verified: bool = False
    regulatory_commitments_reconciled: bool = False
    unresolved_blockers_cleared: bool = False
    cross_entity_control_health_stabilized: bool = False
    sustainability_window_passed: bool = False
    residual_risk_human_decision_recorded: bool = False

class EnterpriseResidualRiskReassessmentRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    residual_systemic_risk_score: float
    release100_enterprise_remediation_execution_version_id: str
    release100_independent_recovery_effectiveness_assurance_version_id: str
    independent_outcome_validation_version_id: str
    sustainability_assessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRecoveryRecertificationRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    release100_enterprise_remediation_execution_version_id: str
    release100_independent_recovery_effectiveness_assurance_version_id: str
    independent_outcome_validation_version_id: str
    residual_risk_decision_version_id: str
    residual_risk_decision: str
    sustainability_assessment_version_id: str
    reclosure_readiness_confirmed: bool = False
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseSustainabilityReclosureRequest(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: str
    systemic_recovery_recertification_version_id: str
    sustainability_assurance_passed: bool = False
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseOutcomeAnalysisRequest(BaseModel):
    recovery_program_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
