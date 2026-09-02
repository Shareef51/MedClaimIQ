from datetime import date
from pydantic import BaseModel,Field

class RegisterDisputeEvidenceRequest(BaseModel):
    evidence_id:str=Field(min_length=3,max_length=128);trace_id:str|None=None
class RegisterFHIRDisputeEvidenceRequest(BaseModel):
    snapshot_id:str=Field(min_length=3,max_length=128);trace_id:str|None=None
class AddProviderAgreementRequest(BaseModel):
    provider_organization_id:str;agreement_key:str;version:str;title:str;effective_from:date;effective_to:date|None=None;content_text:str=Field(min_length=20);metadata:dict=Field(default_factory=dict)
class AddReimbursementPolicyRequest(BaseModel):
    policy_key:str;version:str;title:str;effective_from:date;effective_to:date|None=None;content_text:str=Field(min_length=20);metadata:dict=Field(default_factory=dict)
class SearchDisputeEvidenceRequest(BaseModel):
    query:str=Field(min_length=3,max_length=2000);limit:int=Field(default=12,ge=1,le=30);trace_id:str|None=None
class RunDisputeRecommendationRequest(BaseModel):
    query:str|None=None;idempotency_key:str=Field(min_length=8,max_length=180);trace_id:str|None=None
class RequestDisputeEvidenceRequest(BaseModel):
    document_types:list[str]=Field(min_length=1,max_length=10);rationale:str=Field(min_length=20,max_length=4000);idempotency_key:str=Field(min_length=8,max_length=180)
class ProviderDisputeResponseRequest(BaseModel):
    request_id:str|None=None;statement:str=Field(min_length=20,max_length=8000);evidence_refs:list[str]=Field(default_factory=list,max_length=50);idempotency_key:str=Field(min_length=8,max_length=180)
