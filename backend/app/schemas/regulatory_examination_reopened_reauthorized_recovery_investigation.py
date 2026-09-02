from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReopenedReauthorizedRecoveryInvestigationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    release90_reopening_version_id: str
    investigation_scope: str
    hypothesis: str
    surveillance_version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedRecoveryEvidenceReconstructionRequest(BaseModel):
    recovery_program_id: str
    cycles: list[dict[str, Any]] = Field(default_factory=list)

class RepeatedFailureRootCauseReconstructionRequest(BaseModel):
    recovery_program_id: str
    prior_root_cause_ids: list[str] = Field(default_factory=list)
    current_root_cause_ids: list[str] = Field(default_factory=list)
    historical_root_cause_ids: list[str] = Field(default_factory=list)
    repeated_control_failure_count: int = 0
    systemic_risk_rebound_confirmed: bool = False
    cross_entity_recurrence_confirmed: bool = False

class PriorRecertificationAssumptionReassessmentRequest(BaseModel):
    recovery_program_id: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)

class ReRehabilitationFailureAnalysisRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class ReopenedCrossEntityCausalityRequest(BaseModel):
    recovery_program_id: str
    causal_links: list[dict[str, Any]] = Field(default_factory=list)

class ReopenedRecoveryRegulatorFollowupImpactRequest(BaseModel):
    recovery_program_id: str
    followups: list[dict[str, Any]] = Field(default_factory=list)

class RenewedReauthorizedRecoveryStrategyCandidateCreate(BaseModel):
    recovery_program_id: str
    release90_reopening_version_id: str
    investigation_version_id: str
    strategy_summary: str
    target_root_cause_ids: list[str] = Field(default_factory=list)
    target_control_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    commitment_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedRecoveryIndependentChallengeCreate(BaseModel):
    recovery_program_id: str
    reviewer_role: str
    decision: Literal["agree", "challenge", "request_more_evidence", "escalate"]
    investigation_version_id: str
    strategy_candidate_version_id: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedRecoveryReauthorizationReadinessRequest(BaseModel):
    recovery_program_id: str
    release90_human_reopening_verified: bool = False
    multi_cycle_evidence_reconstructed: bool = False
    prior_recertification_assumptions_reassessed: bool = False
    repeated_failure_root_cause_human_confirmed: bool = False
    cross_entity_causality_human_validated: bool = False
    failed_re_rehabilitation_assessed: bool = False
    regulator_followups_human_interpreted: bool = False
    renewed_recovery_strategy_documented: bool = False
    independent_internal_audit_challenge_complete: bool = False
    executive_review_complete: bool = False

class SupervisoryRecoveryReauthorizationCreate(BaseModel):
    recovery_program_id: str
    actor_role: str
    decision: Literal["authorize", "reject", "defer"]
    release90_reopening_version_id: str
    investigation_version_id: str
    investigation_conclusion_version_id: str
    strategy_candidate_version_id: str
    independent_challenge_version_id: str
    rationale: str
    readiness: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)

class ReopenedRecoveryInvestigationConclusionCreate(BaseModel):
    recovery_program_id: str
    investigator_role: str
    investigation_version_id: str
    conclusion: str
    confirmed_root_cause_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
