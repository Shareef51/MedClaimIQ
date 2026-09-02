from __future__ import annotations
from typing import Any
from pydantic import BaseModel,Field
class RenewedRecoveryProgramCreate(BaseModel): intervention_program_id:str; authorization_version_id:str; program_summary:str; entity_ids:list[str]=Field(default_factory=list); workstreams:list[dict[str,Any]]=Field(default_factory=list); regulatory_commitment_ids:list[str]=Field(default_factory=list); actor_role:str="recovery_governance"
class ControlRehabilitationRequest(BaseModel): intervention_program_id:str; controls:list[dict[str,Any]]=Field(default_factory=list)
class MilestoneCriticalPathRequest(BaseModel): intervention_program_id:str; milestones:list[dict[str,Any]]=Field(default_factory=list)
class ImplementationDriftRequest(BaseModel): intervention_program_id:str; planned_controls:list[dict[str,Any]]=Field(default_factory=list); implemented_controls:list[dict[str,Any]]=Field(default_factory=list)
class RecoveryKPIRequest(BaseModel): intervention_program_id:str; metrics:list[dict[str,Any]]=Field(default_factory=list)
class IndependentRecoveryRevalidationRequest(BaseModel): intervention_program_id:str; reviewer_role:str; tests:list[dict[str,Any]]=Field(default_factory=list); conclusion:str="pending"; evidence_refs:list[str]=Field(default_factory=list)
class ExecutionReadinessRequest(BaseModel): intervention_program_id:str; human_authorization_reference_present:bool=False; program_workstreams_defined:bool=False; control_rehabilitation_scope_approved:bool=False; commitment_mapping_complete:bool=False; critical_path_reviewed:bool=False; execution_evidence_current:bool=False; independent_revalidation_complete:bool=False
class ExecutiveProgressReviewRequest(BaseModel): intervention_program_id:str; actor_role:str; decision:str; rationale:str; progress_snapshot:dict[str,Any]=Field(default_factory=dict); evidence_refs:list[str]=Field(default_factory=list)
