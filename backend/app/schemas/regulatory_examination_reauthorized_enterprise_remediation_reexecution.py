from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class EnterpriseRemediationReExecutionProgramCreate(BaseModel):
    actor_role: str
    remediation_program_id: str
    release103_recovery_program_id: str
    enterprise_remediation_reauthorization_version_id: str
    release103_investigation_version_id: str
    release103_investigation_conclusion_version_id: str
    release103_root_cause_confirmation_version_id: str
    release103_systemic_remediation_failure_classification_version_id: str
    release103_strategy_candidate_version_id: str
    release103_independent_challenge_version_id: str
    release103_human_reauthorization_confirmed: bool
    release103_reauthorization_decision: Literal["authorize","reject","defer"]
    evidence_refs: list[str] = Field(min_length=1)
    workstreams: list[dict[str,Any]] = Field(default_factory=list)

class EnterpriseRemediationReExecutionAnalysisRequest(BaseModel):
    remediation_program_id: str | None = None
    workstreams: list[dict[str,Any]] = Field(default_factory=list)
    root_cause_treatments: list[dict[str,Any]] = Field(default_factory=list)
    controls: list[dict[str,Any]] = Field(default_factory=list)
    deployment_steps: list[dict[str,Any]] = Field(default_factory=list)
    commitments: list[dict[str,Any]] = Field(default_factory=list)
    milestones: list[dict[str,Any]] = Field(default_factory=list)
    planned_controls: list[dict[str,Any]] = Field(default_factory=list)
    implemented_controls: list[dict[str,Any]] = Field(default_factory=list)
    metrics: list[dict[str,Any]] = Field(default_factory=list)
    control_validations: list[dict[str,Any]] = Field(default_factory=list)
    blockers: list[dict[str,Any]] = Field(default_factory=list)

class ControlRetransformationApprovalCreate(BaseModel):
    actor_role: str; remediation_program_id: str; enterprise_remediation_reexecution_version_id: str
    control_ids: list[str] = Field(min_length=1)
    release103_reauthorization_scope_references: list[str] = Field(min_length=1)
    root_cause_treatment_references: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    decision: Literal["approve","reject","revise"]
    rationale: str = Field(min_length=3)

class ImplementationCheckpointCreate(BaseModel):
    actor_role: str; remediation_program_id: str; enterprise_remediation_reexecution_version_id: str
    checkpoint_type: str; status: str
    evidence_refs: list[str] = Field(min_length=1)
    entity_ids: list[str] = Field(default_factory=list); control_ids: list[str] = Field(default_factory=list); root_cause_ids: list[str] = Field(default_factory=list)

class IndependentRecoveryEffectivenessAssuranceCreate(BaseModel):
    reviewer_role: str; remediation_program_id: str; enterprise_remediation_reexecution_version_id: str
    implementation_owner_id: str | None = None
    tests: list[dict[str,Any]] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)

class ExecutionReadinessRequest(BaseModel):
    release103_enterprise_remediation_reauthorization_reference_present: bool=False
    release103_human_reauthorization_confirmed: bool=False
    enterprise_remediation_workstreams_defined: bool=False
    systemic_root_cause_treatments_human_confirmed: bool=False
    systemic_control_retransformation_scope_human_approved: bool=False
    cross_entity_deployment_sequence_validated: bool=False
    regulatory_commitment_alignment_complete: bool=False
    critical_path_reviewed: bool=False
    implementation_evidence_current: bool=False
    systemic_recovery_kpis_baselined: bool=False
    independent_recovery_effectiveness_assurance_complete: bool=False
    enterprise_wide_control_validation_complete: bool=False
    material_blockers_resolved_or_human_escalated: bool=False
    executive_supervisory_review_complete: bool=False

class ExecutiveSupervisoryReviewCreate(BaseModel):
    actor_role: str; remediation_program_id: str; enterprise_remediation_reexecution_version_id: str
    decision: Literal["continue","pause","escalate","require_correction"]
    rationale: str = Field(min_length=3)
    evidence_refs: list[str] = Field(default_factory=list)

class AuditExportRequest(BaseModel):
    remediation_program_id: str | None=None
    version_refs: list[str] = Field(default_factory=list); evidence_refs: list[str] = Field(default_factory=list)
