from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReopenedSupervisoryRecoveryInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release94_enterprise_reopening_version_id: str
    summary: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class MultiCycleSupervisoryEvidenceRequest(BaseModel):
    recovery_program_id: str
    cycles: list[dict[str, Any]] = Field(default_factory=list)

class PersistentEmergentRootCauseRequest(BaseModel):
    recovery_program_id: str
    prior_root_cause_ids: list[str] = Field(default_factory=list)
    historical_root_cause_ids: list[str] = Field(default_factory=list)
    current_root_cause_ids: list[str] = Field(default_factory=list)
    repeated_control_retransformation_failure_count: int = 0
    systemic_risk_rebound_confirmed: bool = False
    cross_entity_recurrence_confirmed: bool = False
    material_regulator_followup_confirmed: bool = False

class PriorRecertificationReclosureAssumptionValidationRequest(BaseModel):
    recovery_program_id: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)

class RepeatedControlRetransformationFailureRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class CrossEntityCausalPropagationRequest(BaseModel):
    recovery_program_id: str
    causal_links: list[dict[str, Any]] = Field(default_factory=list)

class ReopenedSupervisoryRegulatorFollowupImpactRequest(BaseModel):
    recovery_program_id: str
    followups: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseSystemicFailureClassificationRequest(BaseModel):
    recovery_program_id: str
    multi_cycle_root_cause_risk_score: float = 0.0
    failed_control_retransformation_count: int = 0
    affected_entity_count: int = 0
    systemic_risk_rebound_percent: float = 0.0
    repeated_failure_cycle_count: int = 0
    material_regulator_followup_count: int = 0

class HumanRootCauseConfirmationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    root_cause_analysis_version_id: str
    confirmed_persistent_root_cause_ids: list[str] = Field(default_factory=list)
    confirmed_emergent_root_cause_ids: list[str] = Field(default_factory=list)
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class HumanSystemicFailureClassificationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    classification_analysis_version_id: str
    classification: Literal["localized", "material", "enterprise_systemic", "enterprise_critical"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class RenewedEnterpriseRecoveryStrategyCandidateCreate(BaseModel):
    recovery_program_id: str
    release94_enterprise_reopening_version_id: str
    investigation_version_id: str
    root_cause_confirmation_version_id: str
    systemic_failure_classification_version_id: str
    strategy: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedSupervisoryRecoveryIndependentChallengeCreate(BaseModel):
    recovery_program_id: str
    reviewer_role: str
    investigation_version_id: str
    strategy_candidate_version_id: str
    systemic_failure_classification_version_id: str
    decision: Literal["challenge_sustained", "challenge_not_sustained", "request_more_evidence", "escalate"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedSupervisoryRecoveryInvestigationConclusionCreate(BaseModel):
    recovery_program_id: str
    investigator_role: str
    investigation_version_id: str
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRecoveryReauthorizationReadinessRequest(BaseModel):
    release94_human_reopening_verified: bool = False
    formal_investigation_complete: bool = False
    full_multi_cycle_evidence_reconstructed: bool = False
    prior_recertification_reclosure_assumptions_validated: bool = False
    persistent_emergent_root_causes_human_confirmed: bool = False
    repeated_control_retransformation_failure_assessed: bool = False
    cross_entity_causal_propagation_human_validated: bool = False
    regulator_followup_impact_human_interpreted: bool = False
    enterprise_systemic_failure_classification_human_confirmed: bool = False
    renewed_recovery_strategy_documented: bool = False
    independent_internal_audit_challenge_complete: bool = False
    executive_review_complete: bool = False
    evidence_bound_reauthorization_package_complete: bool = False

class EnterpriseRecoveryReauthorizationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["authorize", "reject", "defer"]
    rationale: str
    release94_enterprise_reopening_version_id: str
    investigation_version_id: str
    investigation_conclusion_version_id: str
    root_cause_confirmation_version_id: str
    systemic_failure_classification_version_id: str
    strategy_candidate_version_id: str
    independent_challenge_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    readiness: dict[str, Any] = Field(default_factory=dict)

class ReopenedSupervisoryRecoveryDashboardRequest(BaseModel):
    recovery_program_id: str
    investigation_status: str = "open"
    multi_cycle_root_cause_risk_score: float = 0.0
    enterprise_systemic_failure_score: float = 0.0
    affected_entity_count: int = 0
    repeated_failure_control_count: int = 0
    open_regulator_followup_count: int = 0
    human_reauthorization_pending: bool = True

class ReopenedSupervisoryRecoveryAuditExportRequest(BaseModel):
    recovery_program_id: str
    version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
