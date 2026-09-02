from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
class RepeatedRecoveryFailureInvestigationCreate(BaseModel): recovery_program_id:str; recurrence_escalation_version_id:str; investigation_scope:str; hypothesis:str; evidence_refs:list[str]=Field(default_factory=list)
class RecoveryEvidenceReconstructionRequest(BaseModel): recovery_program_id:str; cycles:list[dict[str,Any]]=Field(default_factory=list)
class RecoveryAssumptionValidationRequest(BaseModel): recovery_program_id:str; assumptions:list[dict[str,Any]]=Field(default_factory=list)
class RecoveryRootCauseReassessmentRequest(BaseModel): recovery_program_id:str; prior_root_cause_ids:list[str]=Field(default_factory=list); current_root_cause_ids:list[str]=Field(default_factory=list); rehabilitation_failed:bool=False; risk_rebound_detected:bool=False
class FailedRehabilitationRequest(BaseModel): recovery_program_id:str; controls:list[dict[str,Any]]=Field(default_factory=list)
class RecoveryCausalityRequest(BaseModel): recovery_program_id:str; causal_links:list[dict[str,Any]]=Field(default_factory=list)
class RegulatorRecoveryImpactRequest(BaseModel): recovery_program_id:str; follow_ups:list[dict[str,Any]]=Field(default_factory=list)
class RenewedRecoveryStrategyCandidateCreate(BaseModel): recovery_program_id:str; strategy_summary:str; target_root_cause_ids:list[str]=Field(default_factory=list); target_control_ids:list[str]=Field(default_factory=list); entity_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class RecoveryIndependentChallengeRequest(BaseModel): recovery_program_id:str; reviewer_role:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class RecoveryReauthorizationReadinessRequest(BaseModel): recovery_program_id:str; recovery_evidence_reconstructed:bool=False; root_cause_human_confirmed:bool=False; cross_entity_scope_validated:bool=False; failed_rehabilitation_assessed:bool=False; independent_internal_audit_challenge_complete:bool=False; regulator_follow_up_assessed:bool=False; renewed_recovery_strategy_documented:bool=False
class RecoveryRemediationReauthorizationRequest(BaseModel): recovery_program_id:str; actor_role:str; decision:str; rationale:str; readiness:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list)
class RecoveryInvestigationConclusionCreate(BaseModel): recovery_program_id:str; investigator_role:str; conclusion:str; root_cause_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
