from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class RemediationPlanCreateRequest(BaseModel):
    finding_code:str;root_cause:str=Field(min_length=8);corrective_action_summary:str=Field(min_length=8);preventive_action_summary:str=Field(min_length=8);control_redesign_proposal:str=Field(min_length=8);financial_impact_analysis:str=Field(min_length=8);accounting_impact_analysis:str=Field(min_length=8);owner_user_id:str;due_at:datetime;use_ai_assistance:bool=False
class RemediationPlanApprovalRequest(BaseModel):approval_rationale:str=Field(min_length=12)
class RemediationTaskCreateRequest(BaseModel):
    task_key:str;task_type:str;description:str=Field(min_length=8);owner_user_id:str;dependency_keys:list[str]=Field(default_factory=list);due_at:datetime
class RemediationTaskCompleteRequest(BaseModel):evidence_refs:list[dict[str,Any]]
class RemediationCheckpointRequest(BaseModel):checkpoint_key:str;checkpoint_type:str;evidence_refs:list[dict[str,Any]]
class ControlRetestRequest(BaseModel):control_key:str;methodology:str=Field(min_length=8);expected_result:str=Field(min_length=5);observed_result:str=Field(min_length=5);outcome:str;evidence_refs:list[dict[str,Any]]
class WaiverRequest(BaseModel):waiver_key:str;waiver_type:str;rationale:str=Field(min_length=8);risk_acceptance:str=Field(min_length=8);expires_at:datetime|None=None
class WaiverDecisionRequest(BaseModel):approve:bool;decision_rationale:str=Field(min_length=8)
class FollowupDraftRequest(BaseModel):response_text:str=Field(min_length=20);cited_refs:list[dict[str,Any]]=Field(default_factory=list)
class FollowupApprovalRequest(BaseModel):approval_rationale:str=Field(min_length=12)
class ClosureCertificationRequest(BaseModel):conclusion:str;closure_rationale:str=Field(min_length=20)
class AIRegulatoryRemediationRecommendation(BaseModel):
    recommendation:str=Field(min_length=10)
    suggested_actions:list[str]=Field(default_factory=list)
    control_redesign_notes:list[str]=Field(default_factory=list)
    financial_accounting_risks:list[str]=Field(default_factory=list)
