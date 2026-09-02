from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class GoldenJourneyRequest(BaseModel):
    journey_id: str
    tenant_id: str
    stages: list[dict[str, Any]] = Field(default_factory=list)
    human_final_decision_recorded: bool = False
    automated_final_claim_decision: bool = False

class ApiContractRegressionRequest(BaseModel):
    checks: list[dict[str, Any]] = Field(default_factory=list)
    breaking_changes: list[dict[str, Any]] = Field(default_factory=list)

class TenantIsolationRequest(BaseModel):
    cases: list[dict[str, Any]] = Field(default_factory=list)
    required_surfaces: list[str] = Field(default_factory=lambda:["sql","vector","cache","object_storage","events","rag","agents"])

class WorkflowRecoveryRequest(BaseModel):
    cases: list[dict[str, Any]] = Field(default_factory=list)

class EventSSEIntegrityRequest(BaseModel):
    cases: list[dict[str, Any]] = Field(default_factory=list)

class FailureInjectionRequest(BaseModel):
    cases: list[dict[str, Any]] = Field(default_factory=list)

class MigrationChainRequest(BaseModel):
    revisions: list[dict[str, Any]] = Field(default_factory=list)
    expected_head: str | None = None

class ReleaseCandidateReadinessRequest(BaseModel):
    gates: dict[str, Any] = Field(default_factory=dict)
    quality_scores: dict[str, float] = Field(default_factory=dict)
    minimum_quality_score: float = 0.90
    evidence_refs: list[str] = Field(default_factory=list)
    release_manifest_ref: str | None = None
    risk_summary: list[dict[str, Any]] = Field(default_factory=list)
    open_findings: list[dict[str, Any]] = Field(default_factory=list)

class IntegrationRunCreate(BaseModel):
    release_id: str
    candidate_version: str
    actor_role: str
    git_sha: str
    release_manifest_ref: str
    evidence_refs: list[str] = Field(default_factory=list)
    gate_results: dict[str, Any] = Field(default_factory=dict)
    quality_scores: dict[str, float] = Field(default_factory=dict)

class ReleaseCandidateDecisionCreate(BaseModel):
    release_id: str
    actor_role: str
    decision: Literal["declare_candidate","reject","defer"]
    integration_run_version_id: str
    readiness: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
