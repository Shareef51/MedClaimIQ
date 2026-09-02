from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class RenewedRemediationPlanCreate(BaseModel):
    commitment_id:str; investigation_id:str; owner_user_id:str; rationale:str; milestone_ids:list[str]=Field(default_factory=list); affected_entity_ids:list[str]=Field(default_factory=list); regulator_follow_up_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class RenewedMilestoneCreate(BaseModel):
    plan_id:str; title:str; owner_user_id:str; due_date:str|None=None; dependency_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class RootCauseComparisonRequest(BaseModel):
    prior:dict[str,Any]; current:dict[str,Any]
class ControlRedesignRecommendationRequest(BaseModel):
    commitment_id:str; control_id:str; recurrence_evidence:list[str]=Field(default_factory=list); current_design:dict[str,Any]=Field(default_factory=dict)
class IndependentRetestCreate(BaseModel):
    commitment_id:str; reviewer_role:str; result:str; rationale:str; scope_entity_ids:list[str]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class ReclosureReadinessRequest(BaseModel):
    renewed_plan_approved:bool=False; all_milestones_complete:bool=False; cross_entity_propagation_complete:bool=False; regulator_follow_up_reconciled:bool=False; independent_retest_passed:bool=False; independent_revalidation_complete:bool=False; evidence_sufficient:bool=False; sustainability_reset_ready:bool=False; second_recurrence_detected:bool=False
class SecondRecurrenceRequest(BaseModel):
    history:list[dict[str,Any]]=Field(default_factory=list)
class SustainabilityResetRequest(BaseModel):
    severity:str="moderate"; recurrence_count:int=1
class HumanRecertificationRequest(BaseModel):
    reviewer_role:str; decision:str; rationale:str; readiness:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list); independent_retest_id:str|None=None
class ReclosureDecisionRequest(BaseModel):
    reviewer_role:str; decision:str; rationale:str; recertification_id:str; sustainability_window:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list)
