from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class InvestigationRequest(BaseModel):
    deficiency_key:str
    enterprise_issue_id:str|None=None
    severity:str=Field(pattern="^(low|moderate|high|critical)$")
    candidate_classification:str=Field(pattern="^(control_deficiency|significant_deficiency_candidate|material_weakness_candidate|other)$")
    cross_control_impacts:list[dict[str,Any]]=Field(default_factory=list)
    root_cause_refs:list[dict[str,Any]]=Field(default_factory=list)
    recurrence_count:int=Field(default=0,ge=0)

class DispositionRequest(BaseModel):
    classification:str=Field(pattern="^(control_deficiency|significant_deficiency|material_weakness|not_a_deficiency|monitoring)$")
    rationale:str=Field(min_length=30)
    independent_challenge:dict[str,Any]=Field(default_factory=dict)

class CorrectiveActionPlanRequest(BaseModel):
    deficiency_key:str
    owner_user_id:str
    title:str=Field(min_length=10,max_length=240)
    actions:list[dict[str,Any]]=Field(min_length=1)
    milestones:list[dict[str,Any]]=Field(default_factory=list)
    regulatory_commitment_refs:list[dict[str,Any]]=Field(default_factory=list)
    compensating_control:dict[str,Any]=Field(default_factory=dict)
    due_at:datetime

class ExecutiveAttestationRequest(BaseModel):
    conclusion:str=Field(pattern="^(closed|remain_open|partially_remediated)$")
    independent_validation_refs:list[dict[str,Any]]=Field(min_length=1)
    retest_refs:list[dict[str,Any]]=Field(min_length=1)
    rationale:str=Field(min_length=30)
