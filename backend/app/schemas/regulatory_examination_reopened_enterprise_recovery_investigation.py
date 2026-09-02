from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReopenedEnterpriseRecoveryInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release98_enterprise_reopening_version_id: str
    summary: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class MultiCycleEnterpriseEvidenceRequest(BaseModel):
    recovery_program_id: str
    cycles: list[dict[str, Any]] = Field(default_factory=list)

class SystemicRecoveryFailureRootCauseRequest(BaseModel):
    recovery_program_id: str
    prior_root_cause_ids: list[str] = Field(default_factory=list)
    historical_root_cause_ids: list[str] = Field(default_factory=list)
    current_root_cause_ids: list[str] = Field(default_factory=list)
    repeated_systemic_control_failure_count: int = 0
    repeated_recovery_failure_cycle_count: int = 0
    systemic_risk_rebound_confirmed: bool = False
    cross_entity_recurrence_confirmed: bool = False
    material_regulatory_commitment_breach_confirmed: bool = False

class PriorEnterpriseRecertificationReclosureAssumptionRequest(BaseModel):
    recovery_program_id: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)

class RepeatedSystemicControlRetransformationFailureRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseCrossEntityCausalPropagationRequest(BaseModel):
    recovery_program_id: str
    causal_links: list[dict[str, Any]] = Field(default_factory=list)

class RegulatoryCommitmentFollowupImpactRequest(BaseModel):
    recovery_program_id: str
    commitments: list[dict[str, Any]] = Field(default_factory=list)
    followups: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseSystemicRecoveryFailureClassificationRequest(BaseModel):
    recovery_program_id: str
    systemic_recovery_failure_root_cause_risk_score: float = 0.0
    failed_systemic_control_retransformation_count: int = 0
    affected_entity_count: int = 0
    systemic_risk_rebound_percent: float = 0.0
    repeated_failure_cycle_count: int = 0
    breached_regulatory_commitment_count: int = 0
    material_regulator_followup_count: int = 0

class EnterpriseRootCauseConfirmationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    root_cause_analysis_version_id: str
    confirmed_persistent_systemic_root_cause_ids: list[str] = Field(default_factory=list)
    confirmed_emergent_systemic_root_cause_ids: list[str] = Field(default_factory=list)
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseSystemicFailureClassificationConfirmationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    investigation_version_id: str
    classification_analysis_version_id: str
    classification: Literal["localized", "material", "enterprise_systemic", "enterprise_critical"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class RenewedEnterpriseRemediationStrategyCandidateCreate(BaseModel):
    recovery_program_id: str
    release98_enterprise_reopening_version_id: str
    investigation_version_id: str
    root_cause_confirmation_version_id: str
    systemic_failure_classification_version_id: str
    strategy: dict[str, Any] = Field(default_factory=dict)
    regulatory_commitment_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRecoveryIndependentChallengeCreate(BaseModel):
    recovery_program_id: str
    reviewer_role: str
    investigation_owner_actor_id: str
    investigation_version_id: str
    strategy_candidate_version_id: str
    systemic_failure_classification_version_id: str
    decision: Literal["challenge_sustained", "challenge_not_sustained", "request_more_evidence", "escalate"]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedEnterpriseRecoveryInvestigationConclusionCreate(BaseModel):
    recovery_program_id: str
    investigator_role: str
    investigation_version_id: str
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseRemediationReauthorizationReadinessRequest(BaseModel):
    release98_human_enterprise_reopening_verified: bool = False
    formal_reopened_enterprise_investigation_complete: bool = False
    full_multi_cycle_enterprise_evidence_reconstructed: bool = False
    prior_enterprise_recertification_reclosure_assumptions_validated: bool = False
    persistent_emergent_systemic_root_causes_human_confirmed: bool = False
    repeated_systemic_control_retransformation_failure_assessed: bool = False
    cross_entity_causal_propagation_human_validated: bool = False
    regulatory_commitment_followup_impact_human_interpreted: bool = False
    enterprise_systemic_failure_classification_human_confirmed: bool = False
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
    release98_enterprise_reopening_version_id: str
    investigation_version_id: str
    investigation_conclusion_version_id: str
    root_cause_confirmation_version_id: str
    systemic_failure_classification_version_id: str
    strategy_candidate_version_id: str
    independent_challenge_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    readiness: dict[str, Any] = Field(default_factory=dict)

class ReopenedEnterpriseRecoveryDashboardRequest(BaseModel):
    recovery_program_id: str
    investigation_status: str = "open"
    systemic_root_cause_risk_score: float = 0.0
    enterprise_systemic_failure_score: float = 0.0
    affected_entity_count: int = 0
    repeated_failure_control_count: int = 0
    breached_commitment_count: int = 0
    open_regulator_followup_count: int = 0
    human_reauthorization_pending: bool = True

class ReopenedEnterpriseRecoveryAuditExportRequest(BaseModel):
    recovery_program_id: str
    version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
