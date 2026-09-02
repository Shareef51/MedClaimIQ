from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class RecoveryOutcomeRequest(BaseModel):
    program_id: str
    baseline_risk_score: float
    current_risk_score: float
    independent_tests: list[dict[str,Any]] = Field(default_factory=list)
    expected_entity_ids: list[str] = Field(default_factory=list)
    completed_entity_ids: list[str] = Field(default_factory=list)

class IndependentRecoveryValidationCreate(BaseModel):
    program_id: str
    actor_role: str
    result: Literal["pass","fail","inconclusive"]
    evidence_refs: list[str] = Field(default_factory=list)
    conclusion: str

class ResidualRiskAcceptanceCreate(BaseModel):
    program_id: str
    actor_role: str
    decision: Literal["accept","reject","defer"]
    rationale: str
    outcome_assessment: dict[str,Any] = Field(default_factory=dict)

class SustainabilityObservationCreate(BaseModel):
    program_id: str
    observation_type: str
    control_health: Literal["healthy","watch","degraded","failed"]
    recurrence_detected: bool = False
    evidence_refs: list[str] = Field(default_factory=list)

class ReclosureReadinessRequest(BaseModel):
    all_workstreams_complete: bool = False
    implementation_evidence_complete: bool = False
    independent_recovery_validation_passed: bool = False
    cross_entity_reconciliation_complete: bool = False
    regulatory_commitments_reconciled: bool = False
    unresolved_blockers: int = 0
    sustainability_window_complete: bool = False
    residual_risk_human_accepted: bool = False

class ExecutiveRecoveryCertificationCreate(BaseModel):
    program_id: str
    actor_role: str
    decision: Literal["certify","reject","defer"]
    rationale: str
    readiness: dict[str,Any] = Field(default_factory=dict)

class ExecutiveReclosureDecisionCreate(BaseModel):
    program_id: str
    actor_role: str
    decision: Literal["reclose","reject","defer"]
    rationale: str
    readiness: dict[str,Any] = Field(default_factory=dict)
