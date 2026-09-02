from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
class SustainabilityObservationCreate(BaseModel):
    commitment_id:str; reclosure_version_id:str; control_id:str; entity_id:str; baseline_control_health:float=100; current_control_health:float=100; days_since_reclosure:int=0; stale_evidence_count:int=0; failed_observation_count:int=0; evidence_refs:list[str]=Field(default_factory=list)
class RepeatRecurrenceRequest(BaseModel):
    commitment_id:str; history:list[dict[str,Any]]=Field(default_factory=list); cross_entity_count:int=0
class ReclosureComparisonRequest(BaseModel): prior:dict[str,Any]; current:dict[str,Any]
class EscalationAssessmentRequest(BaseModel): recurrence_count:int=0; decay_score:float=0; affected_entity_count:int=1; regulator_follow_up_overdue:bool=False
class HumanInvestigationCreate(BaseModel):
    commitment_id:str; escalation_version_id:str; reviewer_role:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list); action:str="investigate"
class GovernanceActionCreate(BaseModel):
    commitment_id:str; investigation_id:str; reviewer_role:str; action_type:str; rationale:str; owner_user_id:str|None=None; evidence_refs:list[str]=Field(default_factory=list)
