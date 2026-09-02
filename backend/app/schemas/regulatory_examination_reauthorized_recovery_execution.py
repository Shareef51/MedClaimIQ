from __future__ import annotations
from typing import Any
from pydantic import BaseModel,Field
class ReauthorizedRecoveryProgramCreate(BaseModel): recovery_program_id:str; remediation_reauthorization_version_id:str; program_summary:str; entity_ids:list[str]=Field(default_factory=list); workstreams:list[dict[str,Any]]=Field(default_factory=list); regulatory_commitment_ids:list[str]=Field(default_factory=list); actor_role:str="recovery_governance"
class ControlReRehabilitationRequest(BaseModel): recovery_program_id:str; controls:list[dict[str,Any]]=Field(default_factory=list)
class DeploymentSequenceRequest(BaseModel): recovery_program_id:str; deployment_steps:list[dict[str,Any]]=Field(default_factory=list)
class CriticalPathRequest(BaseModel): recovery_program_id:str; milestones:list[dict[str,Any]]=Field(default_factory=list)
class ReauthorizedImplementationDriftRequest(BaseModel): recovery_program_id:str; planned_controls:list[dict[str,Any]]=Field(default_factory=list); implemented_controls:list[dict[str,Any]]=Field(default_factory=list)
class ReauthorizedRecoveryKPIRequest(BaseModel): recovery_program_id:str; metrics:list[dict[str,Any]]=Field(default_factory=list)
class IndependentRecoveryAssuranceRequest(BaseModel): recovery_program_id:str; reviewer_role:str; tests:list[dict[str,Any]]=Field(default_factory=list); conclusion:str="pending"; evidence_refs:list[str]=Field(default_factory=list)
class ReauthorizedExecutionReadinessRequest(BaseModel): recovery_program_id:str; human_reauthorization_reference_present:bool=False; reauthorized_workstreams_defined:bool=False; control_rerehabilitation_scope_human_approved:bool=False; cross_entity_sequence_validated:bool=False; regulatory_commitment_alignment_complete:bool=False; critical_path_reviewed:bool=False; execution_evidence_current:bool=False; independent_recovery_assurance_complete:bool=False
class ReauthorizedExecutiveProgressReviewRequest(BaseModel): recovery_program_id:str; actor_role:str; decision:str; rationale:str; progress_snapshot:dict[str,Any]=Field(default_factory=dict); evidence_refs:list[str]=Field(default_factory=list)
