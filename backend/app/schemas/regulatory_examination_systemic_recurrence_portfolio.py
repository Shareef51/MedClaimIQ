from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class PortfolioAggregationRequest(BaseModel):
    portfolio_id: str
    occurrences: list[dict[str, Any]] = Field(default_factory=list)
    regulator_follow_ups: list[dict[str, Any]] = Field(default_factory=list)

class MaterialityAssessmentRequest(BaseModel):
    recurring_commitment_count: int = 0
    affected_entity_count: int = 0
    affected_control_count: int = 0
    affected_examination_count: int = 0
    regulator_count: int = 0
    critical_control_count: int = 0
    overdue_follow_up_count: int = 0
    repeated_root_cause: bool = False

class EnterpriseInterventionCreate(BaseModel):
    portfolio_id: str
    systemic_pattern_id: str
    reviewer_role: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    proposed_program_name: str | None = None

class InterventionProgramDecision(BaseModel):
    intervention_case_id: str
    reviewer_role: str
    decision: str
    rationale: str
    owner_user_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)

class IndependentChallengeCreate(BaseModel):
    intervention_case_id: str
    reviewer_role: str
    conclusion: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
