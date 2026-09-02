from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class SupervisoryRecoveryDecayRequest(BaseModel):
    recovery_program_id: str
    release93_supervisory_sustainability_reclosure_version_id: str
    release93_reclosure_control_health_score: float = 100.0
    current_control_health_score: float = 100.0
    control_retransformation_regressions: int = 0
    prior_supervisory_recovery_failure_cycles: int = 0
    sustainability_breach_count: int = 0
    stale_evidence_count: int = 0
    adverse_control_test_count: int = 0

class SupervisoryControlRetransformationRegressionRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)
    material_regression_threshold_percent: float = 25.0

class SupervisoryRiskReboundRequest(BaseModel):
    recovery_program_id: str
    release93_reclosure_systemic_risk_score: float
    current_systemic_risk_score: float
    peak_post_reclosure_systemic_risk_score: float | None = None
    rebound_threshold_percent: float = 20.0
    absolute_rebound_threshold: float = 15.0

class SupervisoryCrossEntityRecurrenceRequest(BaseModel):
    recovery_program_id: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    expected_entity_count: int | None = None
    propagation_threshold_percent: float = 40.0

class PriorSupervisoryReclosureComparisonRequest(BaseModel):
    recovery_program_id: str
    prior: dict[str, Any] = Field(default_factory=dict)
    current: dict[str, Any] = Field(default_factory=dict)

class SupervisoryExaminationFindingCorrelationRequest(BaseModel):
    recovery_program_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryRegulatorFollowupLinkageRequest(BaseModel):
    recovery_program_id: str
    followups: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseSupervisoryMaterialityRequest(BaseModel):
    recovery_program_id: str
    multi_cycle_supervisory_recovery_decay_score: float = 0.0
    control_retransformation_regression_percent: float = 0.0
    cross_entity_recurrence_percent: float = 0.0
    systemic_risk_rebound_percent: float = 0.0
    prior_supervisory_recovery_failure_cycles: int = 0
    adverse_regulator_followup_count: int = 0

class SupervisoryRecoveryDecayInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release93_supervisory_sustainability_reclosure_version_id: str
    summary: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    enterprise_materiality_version_ref: str | None = None

class SupervisoryIndependentReassessmentCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    result: Literal["confirmed_decay", "not_confirmed", "inconclusive"]
    conclusion: str
    investigation_version_id: str
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisoryExecutiveInternalAuditChallengeCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["escalate", "continue_investigation", "request_more_evidence", "challenge_not_sustained"]
    investigation_version_id: str
    independent_reassessment_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisoryEnterpriseReopeningReadinessRequest(BaseModel):
    release93_supervisory_reclosure_reference_validated: bool = False
    material_multi_cycle_decay_confirmed: bool = False
    human_investigation_complete: bool = False
    independent_reassessment_complete: bool = False
    prior_executive_recertification_reclosure_compared: bool = False
    cross_entity_recurrence_scope_validated: bool = False
    new_examination_finding_links_human_validated: bool = False
    regulator_followups_human_interpreted: bool = False
    enterprise_materiality_human_validated: bool = False
    executive_review_complete: bool = False
    internal_audit_challenge_complete: bool = False
    renewed_recovery_governance_candidate_prepared: bool = False

class SupervisoryEnterpriseReopeningDecisionCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["reopen", "reject", "defer"]
    rationale: str
    release93_supervisory_sustainability_reclosure_version_id: str
    investigation_version_id: str
    independent_reassessment_version_id: str
    supervisory_challenge_version_id: str
    readiness: dict[str, Any] = Field(default_factory=dict)
