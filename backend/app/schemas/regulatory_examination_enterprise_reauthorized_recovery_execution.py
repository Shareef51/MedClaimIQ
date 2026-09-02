from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class EnterpriseRecoveryProgramCreate(BaseModel):
    actor_role: str
    recovery_program_id: str
    enterprise_recovery_reauthorization_version_id: str
    release95_investigation_version_id: str
    release95_investigation_conclusion_version_id: str
    release95_human_reauthorization_confirmed: bool
    release95_reauthorization_decision: Literal["authorize", "do_not_authorize"]
    evidence_refs: list[str] = Field(min_length=1)
    workstreams: list[dict[str, Any]] = Field(default_factory=list)

class EnterpriseRecoveryAnalysisRequest(BaseModel):
    recovery_program_id: str | None = None
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)
    deployment_steps: list[dict[str, Any]] = Field(default_factory=list)
    commitments: list[dict[str, Any]] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    planned_controls: list[dict[str, Any]] = Field(default_factory=list)
    implemented_controls: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    control_validations: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, Any]] = Field(default_factory=list)

class ControlRetransformationApprovalCreate(BaseModel):
    actor_role: str
    recovery_program_id: str
    enterprise_recovery_execution_version_id: str
    control_ids: list[str] = Field(min_length=1)
    release95_reauthorization_scope_references: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    decision: Literal["approve", "reject", "revise"]
    rationale: str = Field(min_length=3)

class ImplementationCheckpointCreate(BaseModel):
    actor_role: str
    recovery_program_id: str
    enterprise_recovery_execution_version_id: str
    checkpoint_type: str
    status: str
    evidence_refs: list[str] = Field(min_length=1)
    entity_ids: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)

class IndependentEffectivenessAssuranceCreate(BaseModel):
    reviewer_role: str
    recovery_program_id: str
    enterprise_recovery_execution_version_id: str
    implementation_owner_id: str | None = None
    tests: list[dict[str, Any]] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)

class ExecutionReadinessRequest(BaseModel):
    release95_enterprise_reauthorization_reference_present: bool = False
    release95_human_reauthorization_confirmed: bool = False
    enterprise_workstreams_defined: bool = False
    systemic_control_retransformation_scope_human_approved: bool = False
    cross_entity_deployment_sequence_validated: bool = False
    regulatory_commitment_alignment_complete: bool = False
    critical_path_reviewed: bool = False
    implementation_evidence_current: bool = False
    systemic_recovery_kpis_baselined: bool = False
    independent_effectiveness_assurance_complete: bool = False
    enterprise_wide_control_validation_complete: bool = False
    material_blockers_resolved_or_human_escalated: bool = False

class ExecutiveSupervisoryReviewCreate(BaseModel):
    actor_role: str
    recovery_program_id: str
    enterprise_recovery_execution_version_id: str
    decision: Literal["continue", "pause", "escalate", "require_correction"]
    rationale: str = Field(min_length=3)
    evidence_refs: list[str] = Field(default_factory=list)

class AuditExportRequest(BaseModel):
    tenant_id: str | None = None
    recovery_program_id: str | None = None
    version_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
