from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class RenewedEnterpriseProgramCreate(BaseModel):
    reauthorization_id: str
    systemic_failure_investigation_id: str
    title: str
    strategy_version_id: str
    entity_ids: list[str] = Field(default_factory=list)
    regulatory_commitment_ids: list[str] = Field(default_factory=list)

class CorrectiveActionWorkstreamCreate(BaseModel):
    program_id: str
    name: str
    owner_id: str
    entity_ids: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)
    milestones: list[dict[str,Any]] = Field(default_factory=list)
    dependencies: list[dict[str,Any]] = Field(default_factory=list)

class ControlTransformationCreate(BaseModel):
    program_id: str
    control_id: str
    current_design_version: str | None = None
    proposed_design_version: str
    transformation_type: Literal["replace","redesign","consolidate","decommission","compensating_control"]
    evidence_refs: list[str] = Field(default_factory=list)

class CriticalPathRequest(BaseModel):
    milestones: list[dict[str,Any]] = Field(default_factory=list)
    dependencies: list[dict[str,Any]] = Field(default_factory=list)

class ImplementationDriftRequest(BaseModel):
    expected_controls: list[dict[str,Any]] = Field(default_factory=list)
    implemented_controls: list[dict[str,Any]] = Field(default_factory=list)

class EffectivenessKpiRequest(BaseModel):
    tests: list[dict[str,Any]] = Field(default_factory=list)
    expected_entity_ids: list[str] = Field(default_factory=list)

class IndependentRecoveryTestCreate(BaseModel):
    program_id: str
    reviewer_role: str
    control_id: str
    entity_id: str
    result: Literal["pass","fail","inconclusive"]
    evidence_refs: list[str] = Field(default_factory=list)
    conclusion: str

class RecoveryReadinessRequest(BaseModel):
    all_required_milestones_complete: bool = False
    implementation_evidence_complete: bool = False
    independent_recovery_testing_passed: bool = False
    cross_entity_validation_complete: bool = False
    critical_path_at_risk: bool = False
    implementation_drift_detected: bool = False

class ResidualSystemicRiskRequest(BaseModel):
    baseline_risk_score: float
    current_risk_score: float

class HumanResidualRiskDecision(BaseModel):
    actor_role: str
    decision: Literal["accept","reject","defer"]
    rationale: str
    readiness: dict[str,Any] = Field(default_factory=dict)
    risk_assessment: dict[str,Any] = Field(default_factory=dict)

class ExecutiveProgressDecision(BaseModel):
    actor_role: str
    decision: Literal["continue","escalate","pause","request_more_evidence"]
    rationale: str
    progress_snapshot: dict[str,Any] = Field(default_factory=dict)
