from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class SupervisoryReauthorizedRecoveryProgramCreate(BaseModel):
    recovery_program_id: str
    supervisory_recovery_reauthorization_version_id: str
    release91_investigation_version_id: str
    program_summary: str
    entity_ids: list[str] = Field(default_factory=list)
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    regulatory_commitment_ids: list[str] = Field(default_factory=list)
    actor_role: str = "recovery_governance"

class SupervisoryProgramProgressRequest(BaseModel):
    recovery_program_id: str
    workstreams: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseControlReTransformationRequest(BaseModel):
    recovery_program_id: str
    controls: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryDeploymentSequenceRequest(BaseModel):
    recovery_program_id: str
    deployment_steps: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryCriticalPathRequest(BaseModel):
    recovery_program_id: str
    milestones: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryImplementationDriftRequest(BaseModel):
    recovery_program_id: str
    planned_controls: list[dict[str, Any]] = Field(default_factory=list)
    implemented_controls: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryRecoveryKPIRequest(BaseModel):
    recovery_program_id: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)

class SupervisoryExecutionCheckpointCreate(BaseModel):
    recovery_program_id: str
    supervisory_recovery_execution_version_id: str
    actor_role: str
    checkpoint_type: str
    status: str
    evidence_refs: list[str] = Field(default_factory=list)
    dependency_ids: list[str] = Field(default_factory=list)
    notes: str = ""

class SupervisoryIndependentRecoveryAssuranceRequest(BaseModel):
    recovery_program_id: str
    supervisory_recovery_execution_version_id: str
    reviewer_role: str
    tests: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = "pending"
    evidence_refs: list[str] = Field(default_factory=list)

class SupervisoryExecutionReadinessRequest(BaseModel):
    recovery_program_id: str
    release91_supervisory_reauthorization_reference_present: bool = False
    supervisory_workstreams_defined: bool = False
    control_retransformation_scope_human_approved: bool = False
    cross_entity_sequence_validated: bool = False
    regulatory_commitment_alignment_complete: bool = False
    critical_path_reviewed: bool = False
    execution_evidence_current: bool = False
    recovery_kpis_baselined: bool = False
    independent_recovery_assurance_complete: bool = False

class SupervisoryExecutiveProgressReviewRequest(BaseModel):
    recovery_program_id: str
    supervisory_recovery_execution_version_id: str
    actor_role: str
    decision: Literal["continue", "escalate", "pause", "request_more_evidence"]
    rationale: str
    progress_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
