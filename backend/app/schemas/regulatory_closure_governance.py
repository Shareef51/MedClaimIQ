from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class ClosurePackageRequest(BaseModel):
    deficiency_key: str
    corrective_action_refs: list[dict[str,Any]] = Field(min_length=1)
    retest_refs: list[dict[str,Any]] = Field(min_length=1)
    independent_validation_refs: list[dict[str,Any]] = Field(min_length=1)
    regulatory_commitment_refs: list[dict[str,Any]] = Field(default_factory=list)
    unresolved_exceptions: list[dict[str,Any]] = Field(default_factory=list)
    compensating_control_exit: dict[str,Any] = Field(default_factory=dict)
    residual_risk: dict[str,Any] = Field(default_factory=dict)

class CertificationRequest(BaseModel):
    conclusion: str = Field(pattern="^(certified_closed|remain_open|conditional)$")
    rationale: str = Field(min_length=30)

class SustainabilityWindowRequest(BaseModel):
    deficiency_key: str
    starts_at: datetime
    ends_at: datetime
    required_observations: int = Field(default=3, ge=1, le=100)

class SustainabilityObservationRequest(BaseModel):
    passed: bool
    recurrence_detected: bool = False

class ReopenDecisionRequest(BaseModel):
    trigger: str = Field(min_length=5,max_length=80)
    evidence_refs: list[dict[str,Any]] = Field(min_length=1)
    decision: str = Field(pattern="^(reopen|keep_closed|monitor)$")
    rationale: str = Field(min_length=30)
