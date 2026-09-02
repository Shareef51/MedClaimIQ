from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReauthorizedRecoveryDecayRequest(BaseModel):
    recovery_program_id:str
    reclosure_control_health_score:float=100.0
    current_control_health_score:float=100.0
    repeated_failure_control_regressions:int=0
    sustainability_breach_count:int=0
    stale_evidence_count:int=0
    days_since_reclosure:int=0
    prior_recovery_failure_cycles:int=0

class ReauthorizedRiskReboundRequest(BaseModel):
    recovery_program_id:str
    reclosure_systemic_risk_score:float
    current_systemic_risk_score:float
    peak_post_reclosure_risk_score:float|None=None
    rebound_threshold_percent:float=20.0
    absolute_rebound_threshold:float=15.0

class CrossEntityRecurrenceRequest(BaseModel):
    recovery_program_id:str
    entities:list[dict[str,Any]]=Field(default_factory=list)
    expected_entity_count:int|None=None
    propagation_threshold_percent:float=40.0

class PriorReclosureComparisonRequest(BaseModel):
    recovery_program_id:str
    prior:dict[str,Any]=Field(default_factory=dict)
    current:dict[str,Any]=Field(default_factory=dict)

class ExaminationFindingCorrelationRequest(BaseModel):
    recovery_program_id:str
    items:list[dict[str,Any]]=Field(default_factory=list)

class RegulatorFollowupLinkageRequest(BaseModel):
    recovery_program_id:str
    followups:list[dict[str,Any]]=Field(default_factory=list)

class ReauthorizedRecoveryDecayInvestigationCreate(BaseModel):
    recovery_program_id:str
    actor_role:str
    summary:str
    surveillance_version_refs:list[str]=Field(default_factory=list)
    evidence_refs:list[str]=Field(default_factory=list)
    prior_recertification_version_id:str|None=None
    prior_reclosure_version_id:str|None=None

class IndependentRecoveryReassessmentCreate(BaseModel):
    recovery_program_id:str
    actor_role:str
    result:Literal["confirmed_decay","not_confirmed","inconclusive"]
    conclusion:str
    evidence_refs:list[str]=Field(default_factory=list)
    investigation_version_id:str

class SupervisoryRecoveryChallengeCreate(BaseModel):
    recovery_program_id:str
    actor_role:str
    decision:Literal["escalate","continue_investigation","request_more_evidence","challenge_not_sustained"]
    investigation_version_id:str
    independent_reassessment_version_id:str
    rationale:str
    evidence_refs:list[str]=Field(default_factory=list)

class EnterpriseRecoveryReopeningReadinessRequest(BaseModel):
    material_decay_confirmed:bool=False
    human_investigation_complete:bool=False
    independent_reassessment_complete:bool=False
    prior_recertification_reclosure_compared:bool=False
    cross_entity_scope_validated:bool=False
    new_examination_finding_links_human_validated:bool=False
    regulator_followups_human_interpreted:bool=False
    executive_review_complete:bool=False
    internal_audit_challenge_complete:bool=False
    renewed_recovery_governance_candidate_prepared:bool=False

class EnterpriseRecoveryReopeningDecisionCreate(BaseModel):
    recovery_program_id:str
    actor_role:str
    decision:Literal["reopen","reject","defer"]
    rationale:str
    readiness:dict[str,Any]=Field(default_factory=dict)
    investigation_version_id:str
    independent_reassessment_version_id:str
    supervisory_challenge_version_id:str
