from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class InterventionProgramPlanCreate(BaseModel):
    intervention_case_id: str
    program_name: str
    reviewer_role: str
    rationale: str
    executive_owner_user_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    regulatory_commitment_links: list[dict[str, Any]] = Field(default_factory=list)
    required_entity_ids: list[str] = Field(default_factory=list)

class ProgramExecutionAssessmentRequest(BaseModel):
    intervention_program_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    required_entity_ids: list[str] = Field(default_factory=list)
    validated_entity_ids: list[str] = Field(default_factory=list)
    regulatory_commitment_links: list[dict[str, Any]] = Field(default_factory=list)

class ImplementationCheckpointCreate(BaseModel):
    intervention_program_id: str
    workstream_id: str
    entity_id: str
    checkpoint_type: str
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_hashes: list[str] = Field(default_factory=list)
    implementation_status: str

class ResourceCapacityAssessmentRequest(BaseModel):
    intervention_program_id: str
    available_capacity: float = 0
    planned_demand: float = 0
    critical_workstream_count: int = 0
    overdue_milestone_count: int = 0

class IndependentEffectivenessAssessmentRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    independent_tests: list[dict[str, Any]] = Field(default_factory=list)
    required_entity_ids: list[str] = Field(default_factory=list)
    residual_systemic_risk_score: float = 100
    maximum_certifiable_residual_risk: float = 25
    rationale: str

class ExecutiveCertificationRequest(BaseModel):
    intervention_program_id: str
    reviewer_role: str
    decision: str
    rationale: str
    independent_assurance_version_id: str
    residual_systemic_risk_score: float
    evidence_refs: list[str] = Field(default_factory=list)

class DependencyConcentrationRequest(BaseModel):
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
