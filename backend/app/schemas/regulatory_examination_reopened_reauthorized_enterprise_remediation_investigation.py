from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReopenedReauthorizedEnterpriseRemediationInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release102_enterprise_recovery_reopening_version_id: str
    release102_human_enterprise_reopening_verified: bool = False
    summary: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class MultiCycleRemediationEvidenceRequest(BaseModel):
    recovery_program_id: str
    cycles: list[dict[str, Any]] = Field(default_factory=list)

class PersistentEmergentTreatmentFailureRequest(BaseModel):
    recovery_program_id: str
    treatments: list[dict[str, Any]] = Field(default_factory=list)
    material_failure_threshold_percent: float = 20.0

class SystemicRemediationFailureRootCauseRequest(BaseModel):
    recovery_program_id: str
    prior_confirmed_root_cause_ids: list[str] = Field(default_factory=list)
    treated_root_cause_ids: list[str] = Field(default_factory=list)
    current_root_cause_ids: list[str] = Field(default_factory=list)
    failed_root_cause_treatment_count: int = 0
    repeated_systemic_control_failure_count: int = 0
    repeated_remediation_failure_cycle_count: int = 0
    systemic_risk_rebound_confirmed: bool = False
    cross_entity_recurrence_confirmed: bool = False
    material_regulatory_commitment_breach_confirmed: bool = False

class PriorRecertificationReclosureAssumptionRequest(BaseModel):
    recovery_program_id: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)

class RepeatedSystemicControlRetransformationFailureRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class RemediationCrossEntityCausalPropagationRequest(BaseModel):
    recovery_program_id: str
    causal_links: list[dict[str, Any]] = Field(default_factory=list)

class RemediationRegulatoryCommitmentFollowupImpactRequest(BaseModel):
    recovery_program_id: str
    commitments: list[dict[str, Any]] = Field(default_factory=list)
    followups: list[dict[str, Any]] = Field(default_factory=list)

class SystemicRemediationFailureClassificationRequest(BaseModel):
    recovery_program_id: str
    systemic_remediation_failure_root_cause_risk_score: float = 0.0
    failed_root_cause_treatment_count: int = 0
    failed_systemic_control_retransformation_count: int = 0
    affected_entity_count: int = 0
    systemic_risk_rebound_percent: float = 0.0
    repeated_remediation_failure_cycle_count: int = 0
    breached_regulatory_commitment_count: int = 0
    material_regulator_followup_count: int = 0

class RemediationRootCauseConfirmationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    root_cause_analysis_version_id: str
    confirmed_persistent_root_cause_ids: list[str] = Field(default_factory=list)
    confirmed_emergent_root_cause_ids: list[str] = Field(default_factory=list)
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class SystemicRemediationFailureClassificationConfirmationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    classification_analysis_version_id: str
    classification: Literal["localized", "material", "enterprise_systemic", "enterprise_critical"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class RenewedEnterpriseRemediationStrategyCandidateCreate(BaseModel):
    recovery_program_id: str
    release102_enterprise_recovery_reopening_version_id: str
    investigation_version_id: str
    root_cause_confirmation_version_id: str
    systemic_remediation_failure_classification_version_id: str
    strategy: dict[str, Any] = Field(default_factory=dict)
    regulatory_commitment_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRemediationIndependentChallengeCreate(BaseModel):
    recovery_program_id: str
    reviewer_role: str
    investigation_owner_actor_id: str
    investigation_version_id: str
    strategy_candidate_version_id: str
    systemic_remediation_failure_classification_version_id: str
    decision: Literal["challenge_sustained", "challenge_not_sustained", "request_more_evidence", "escalate"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedRemediationInvestigationConclusionCreate(BaseModel):
    recovery_program_id: str
    investigator_role: str
    investigation_version_id: str
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRemediationReauthorizationReadinessRequest(BaseModel):
    release102_human_enterprise_reopening_verified: bool = False
    formal_reopened_remediation_investigation_complete: bool = False
    full_multi_cycle_remediation_evidence_reconstructed: bool = False
    persistent_emergent_treatment_failure_human_validated: bool = False
    prior_recertification_reclosure_assumptions_validated: bool = False
    systemic_remediation_failure_root_causes_human_confirmed: bool = False
    repeated_systemic_control_retransformation_failure_assessed: bool = False
    cross_entity_causal_propagation_human_validated: bool = False
    regulatory_commitment_followup_impact_human_interpreted: bool = False
    systemic_remediation_failure_classification_human_confirmed: bool = False
    renewed_enterprise_remediation_strategy_documented: bool = False
    independent_internal_audit_challenge_complete: bool = False
    segregation_of_duties_confirmed: bool = False
    executive_review_complete: bool = False
    evidence_bound_reauthorization_package_complete: bool = False

class EnterpriseRemediationReauthorizationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["authorize", "reject", "defer"]
    rationale: str
    release102_enterprise_recovery_reopening_version_id: str
    investigation_version_id: str
    investigation_conclusion_version_id: str
    root_cause_confirmation_version_id: str
    systemic_remediation_failure_classification_version_id: str
    strategy_candidate_version_id: str
    independent_challenge_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    readiness: dict[str, Any] = Field(default_factory=dict)

class ReopenedRemediationDashboardRequest(BaseModel):
    recovery_program_id: str
    investigation_status: str = "open"
    systemic_remediation_failure_root_cause_risk_score: float = 0.0
    systemic_remediation_failure_score: float = 0.0
    failed_root_cause_treatment_count: int = 0
    failed_systemic_control_count: int = 0
    affected_entity_count: int = 0
    breached_commitment_count: int = 0
    human_reauthorization_pending: bool = True

class ReopenedRemediationAuditExportRequest(BaseModel):
    recovery_program_id: str
    version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
