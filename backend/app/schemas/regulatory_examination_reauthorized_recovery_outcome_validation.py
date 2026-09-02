from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class ReauthorizedRecoveryOutcomeRequest(BaseModel):
    recovery_program_id:str
    workstreams:list[dict[str,Any]]=Field(default_factory=list)
    controls:list[dict[str,Any]]=Field(default_factory=list)
class ReauthorizedSystemicRiskReductionRequest(BaseModel):
    recovery_program_id:str; baseline_systemic_risk_score:float; current_systemic_risk_score:float; minimum_required_reduction_percent:float=30.0
class ReauthorizedCrossEntityCompletionRequest(BaseModel):
    recovery_program_id:str; entities:list[dict[str,Any]]=Field(default_factory=list)
class RepeatedFailureControlEffectivenessRequest(BaseModel):
    recovery_program_id:str; controls:list[dict[str,Any]]=Field(default_factory=list)
class IndependentRecoveryOutcomeAssuranceRequest(BaseModel):
    recovery_program_id:str; reviewer_role:str; tests:list[dict[str,Any]]=Field(default_factory=list); conclusion:str="pending"; evidence_refs:list[str]=Field(default_factory=list)
class ReauthorizedRegulatoryCommitmentCompletionRequest(BaseModel):
    recovery_program_id:str; commitments:list[dict[str,Any]]=Field(default_factory=list)
class ReauthorizedSustainabilityWindowRequest(BaseModel):
    recovery_program_id:str; observed_window_days:int=0; minimum_window_days:int=60; minimum_control_health_score:float=85.0; observations:list[dict[str,Any]]=Field(default_factory=list)
class ReauthorizedReclosureReadinessRequest(BaseModel):
    recovery_program_id:str
    reauthorized_recovery_outcomes_complete:bool=False
    cross_entity_completion_reconciled:bool=False
    repeated_failure_controls_effective:bool=False
    independent_recovery_outcome_validated:bool=False
    systemic_risk_reduction_verified:bool=False
    unresolved_blockers_cleared:bool=False
    regulatory_commitments_reconciled:bool=False
    sustainability_window_passed:bool=False
    residual_risk_human_decision_recorded:bool=False
class ReauthorizedResidualRiskReassessmentRequest(BaseModel):
    recovery_program_id:str; actor_role:str; decision:str; residual_systemic_risk_score:float; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class ReauthorizedRecoveryRecertificationRequest(BaseModel):
    recovery_program_id:str; actor_role:str; decision:str; independent_outcome_validation_version_id:str; residual_risk_decision_version_id:str; sustainability_assessment_version_id:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class ReauthorizedSustainabilityReclosureRequest(BaseModel):
    recovery_program_id:str; actor_role:str; decision:str; recovery_recertification_version_id:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
