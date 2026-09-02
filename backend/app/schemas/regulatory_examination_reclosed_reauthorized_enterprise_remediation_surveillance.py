from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class EnterpriseRecoveryDecayRequest(BaseModel):
    recovery_program_id: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    release101_reclosure_control_health_score: float = 100.0
    current_control_health_score: float = 100.0
    systemic_control_retransformation_regressions: int = 0
    prior_enterprise_recovery_failure_cycles: int = 0
    sustainability_breach_count: int = 0
    stale_evidence_count: int = 0
    adverse_control_test_count: int = 0
    regulatory_commitment_breach_count: int = 0


class RootCauseTreatmentDecayRequest(BaseModel):
    recovery_program_id: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    root_cause_treatments: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_treatment_decay_threshold_percent: float = 20.0

class SystemicControlRetransformationRegressionRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)
    material_regression_threshold_percent: float = 20.0

class EnterpriseRiskReboundRequest(BaseModel):
    recovery_program_id: str
    release101_reclosure_systemic_risk_score: float
    current_systemic_risk_score: float
    peak_post_reclosure_systemic_risk_score: float | None = None
    rebound_threshold_percent: float = 20.0
    absolute_rebound_threshold: float = 15.0

class EnterpriseCrossEntityRecurrenceRequest(BaseModel):
    recovery_program_id: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    expected_entity_count: int | None = None
    propagation_threshold_percent: float = 35.0

class PriorEnterpriseReclosureComparisonRequest(BaseModel):
    recovery_program_id: str
    prior: dict[str, Any] = Field(default_factory=dict)
    current: dict[str, Any] = Field(default_factory=dict)

class EnterpriseExaminationFindingCorrelationRequest(BaseModel):
    recovery_program_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseRegulatorFollowupLinkageRequest(BaseModel):
    recovery_program_id: str
    followups: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseMaterialityRequest(BaseModel):
    recovery_program_id: str
    multi_cycle_enterprise_recovery_decay_score: float = 0.0
    systemic_control_retransformation_regression_percent: float = 0.0
    cross_entity_recurrence_percent: float = 0.0
    systemic_risk_rebound_percent: float = 0.0
    prior_enterprise_recovery_failure_cycles: int = 0
    adverse_regulator_followup_count: int = 0
    regulatory_commitment_breach_count: int = 0

class EnterpriseRecoveryDecayInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    summary: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    enterprise_materiality_version_ref: str | None = None

class EnterpriseIndependentReassessmentCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    result: Literal["confirmed_decay", "not_confirmed", "inconclusive"]
    conclusion: str
    investigation_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    investigation_owner_id: str | None = None

class EnterpriseExecutiveInternalAuditChallengeCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["escalate", "continue_investigation", "request_more_evidence", "challenge_not_sustained"]
    investigation_version_id: str
    independent_reassessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class EnterpriseReopeningReadinessRequest(BaseModel):
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_reference_validated: bool = False
    material_systemic_recovery_decay_confirmed: bool = False
    root_cause_treatment_decay_scope_human_validated: bool = False
    human_investigation_complete: bool = False
    independent_reassessment_complete: bool = False
    prior_executive_recertification_reclosure_compared: bool = False
    cross_entity_recurrence_scope_validated: bool = False
    new_examination_finding_links_human_validated: bool = False
    regulator_followups_human_interpreted: bool = False
    enterprise_materiality_human_validated: bool = False
    executive_review_complete: bool = False
    internal_audit_challenge_complete: bool = False
    renewed_enterprise_recovery_governance_candidate_prepared: bool = False

class EnterpriseReopeningDecisionCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["reopen", "reject", "defer"]
    rationale: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    investigation_version_id: str
    independent_reassessment_version_id: str
    enterprise_challenge_version_id: str
    readiness: dict[str, Any] = Field(default_factory=dict)

class EnterpriseSurveillanceDashboardRequest(BaseModel):
    recovery_program_id: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_treatments: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    followups: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    release101_reclosure_control_health_score: float = 100.0
    current_control_health_score: float = 100.0
    release101_reclosure_systemic_risk_score: float = 0.0
    current_systemic_risk_score: float = 0.0
    systemic_control_retransformation_regressions: int = 0
    prior_enterprise_recovery_failure_cycles: int = 0
    sustainability_breach_count: int = 0
    stale_evidence_count: int = 0
    adverse_control_test_count: int = 0
    regulatory_commitment_breach_count: int = 0

class EnterpriseAuditExportRequest(BaseModel):
    recovery_program_id: str
    release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)
