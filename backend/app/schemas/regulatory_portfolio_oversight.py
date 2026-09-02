from datetime import datetime
from typing import Any
from pydantic import BaseModel,Field
class EnterpriseControlCreateRequest(BaseModel):control_key:str;name:str=Field(min_length=4);description:str=Field(min_length=8);control_family:str;owner_user_id:str
class ControlFindingMapRequest(BaseModel):plan_id:str;mapping_rationale:str=Field(min_length=8)
class PortfolioSnapshotRequest(BaseModel):period_key:str
class TestingCampaignRequest(BaseModel):campaign_key:str;methodology:str=Field(min_length=12);control_ids:list[str];due_at:datetime
class TestingResultRequest(BaseModel):control_id:str;outcome:str;observations:str=Field(min_length=8);evidence_refs:list[dict[str,Any]]=Field(default_factory=list)
class RiskAcceptanceRequest(BaseModel):risk_key:str;rationale:str=Field(min_length=12);expires_at:datetime
class RiskAcceptanceDecisionRequest(BaseModel):approve:bool;decision_rationale:str=Field(min_length=12)
class ManagementAttestationRequest(BaseModel):conclusion:str;rationale:str=Field(min_length=20)
class PortfolioCertificationRequest(BaseModel):conclusion:str;rationale:str=Field(min_length=20)
