from pydantic import BaseModel,Field
class SettlementIntelligenceInvestigationRequest(BaseModel):exception_code:str=Field(min_length=3,max_length=100)
class SettlementIntelligenceCopilotRequest(BaseModel):
    query:str=Field(min_length=3,max_length=4000);provider_organization_id:str|None=Field(default=None,max_length=128);settlement_case_id:str|None=Field(default=None,max_length=128);top_k:int=Field(default=8,ge=1,le=25)
class StatementPublishRequest(BaseModel):idempotency_key:str=Field(min_length=3,max_length=180)
