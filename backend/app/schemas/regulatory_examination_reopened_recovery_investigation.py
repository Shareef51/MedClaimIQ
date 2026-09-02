from __future__ import annotations
from typing import Any
from pydantic import BaseModel,Field
class ReopenedRecoveryInvestigationCreate(BaseModel): intervention_program_id:str; reopening_version_id:str; investigation_scope:str; hypothesis:str; evidence_refs:list[str]=Field(default_factory=list); actor_role:str="regulatory_affairs"
class SystemicDecayReconstructionRequest(BaseModel): intervention_program_id:str; decay_cycles:list[dict[str,Any]]=Field(default_factory=list)
class RecoveryAssumptionValidationRequest(BaseModel): intervention_program_id:str; assumptions:list[dict[str,Any]]=Field(default_factory=list)
class DecayRootCauseReassessmentRequest(BaseModel): intervention_program_id:str; prior_root_cause_ids:list[str]=Field(default_factory=list); current_root_cause_ids:list[str]=Field(default_factory=list); recovery_control_failed:bool=False
class CrossEntityControlGapRequest(BaseModel): intervention_program_id:str; control_gaps:list[dict[str,Any]]=Field(default_factory=list)
class RegulatorFollowUpImpactRequest(BaseModel): intervention_program_id:str; follow_ups:list[dict[str,Any]]=Field(default_factory=list)
class CommitmentAlignmentRequest(BaseModel): intervention_program_id:str; commitments:list[dict[str,Any]]=Field(default_factory=list)
class RenewedRecoveryStrategyCreate(BaseModel): intervention_program_id:str; strategy_summary:str; root_cause_ids:list[str]=Field(default_factory=list); control_ids:list[str]=Field(default_factory=list); entity_ids:list[str]=Field(default_factory=list); regulatory_commitment_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class IndependentChallengeRequest(BaseModel): intervention_program_id:str; reviewer_role:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class AuthorizationReadinessRequest(BaseModel): intervention_program_id:str; systemic_decay_reconstructed:bool=False; root_cause_human_confirmed:bool=False; cross_entity_gap_scope_validated:bool=False; regulator_follow_up_assessed:bool=False; commitment_alignment_complete:bool=False; independent_challenge_complete:bool=False; renewed_strategy_documented:bool=False
class RenewedRemediationAuthorizationRequest(BaseModel): intervention_program_id:str; actor_role:str; decision:str; rationale:str; readiness:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list)
