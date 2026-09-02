from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class RecoverySurveillanceAssessment(BaseModel):
    program_id: str
    closure_residual_risk_score: float
    current_systemic_risk_score: float
    closure_control_effectiveness: float = 100.0
    current_control_effectiveness: float = 100.0
    expected_entity_ids: list[str] = Field(default_factory=list)
    regressed_entity_ids: list[str] = Field(default_factory=list)
    new_examination_match: bool = False
    regulator_follow_up_adverse: bool = False
    risk_rebound_threshold_percent: float = 20.0
    control_decay_threshold_points: float = 10.0

class ExaminationMatchRequest(BaseModel):
    program_id: str
    examination_id: str
    root_cause_similarity: float = 0.0
    control_overlap: float = 0.0
    entity_overlap: float = 0.0
    regulatory_obligation_overlap: float = 0.0
    match_threshold: float = 70.0

class SustainabilityBreachInvestigationCreate(BaseModel):
    program_id: str
    actor_role: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    prior_recovery_certification_ref: str | None = None
    regulator_follow_up_refs: list[str] = Field(default_factory=list)

class IndependentReassessmentCreate(BaseModel):
    program_id: str
    actor_role: str
    result: Literal["confirmed_decay","not_confirmed","inconclusive"]
    conclusion: str
    evidence_refs: list[str] = Field(default_factory=list)

class ReopeningReadinessRequest(BaseModel):
    sustainability_breach_confirmed: bool = False
    investigation_complete: bool = False
    independent_reassessment_complete: bool = False
    executive_review_complete: bool = False
    internal_audit_review_complete: bool = False
    prior_certification_compared: bool = False
    renewed_remediation_candidate_prepared: bool = False

class EnterpriseReopeningDecisionCreate(BaseModel):
    program_id: str
    actor_role: str
    decision: Literal["reopen","reject","defer"]
    rationale: str
    readiness: dict[str,Any] = Field(default_factory=dict)
