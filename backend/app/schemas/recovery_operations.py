from decimal import Decimal
from pydantic import BaseModel,Field

class CreateRecoveryCaseRequest(BaseModel):
    proposal_id:str=Field(min_length=3,max_length=128);idempotency_key:str=Field(min_length=8,max_length=160)
class AcquireRecoveryLeaseRequest(BaseModel):
    expected_case_version:int=Field(ge=1);lease_minutes:int=Field(default=30,ge=5,le=120)
class VerifyRecoveryOutcomeRequest(BaseModel):
    lease_token:str=Field(min_length=16);idempotency_key:str=Field(min_length=8,max_length=160)
class RecordRecoveryRequest(BaseModel):
    amount:Decimal=Field(gt=0);currency:str=Field(min_length=3,max_length=3);external_reference:str=Field(min_length=3,max_length=180);evidence_details:dict=Field(default_factory=dict);lease_token:str=Field(min_length=16);idempotency_key:str=Field(min_length=8,max_length=160)
class ProviderDisputeRequest(BaseModel):
    external_reference:str=Field(min_length=3,max_length=180);disputed_amount:Decimal=Field(gt=0);currency:str=Field(min_length=3,max_length=3);reason_code:str=Field(min_length=2,max_length=100);statement:str=Field(min_length=10,max_length=10000);evidence_refs:list[str]=Field(default_factory=list,max_length=100);idempotency_key:str=Field(min_length=8,max_length=160)
class ResolveProviderDisputeRequest(BaseModel):
    outcome:str=Field(min_length=3,max_length=80);rationale:str=Field(min_length=10,max_length=5000);resolution_amount:Decimal|None=None;idempotency_key:str=Field(min_length=8,max_length=160)
class RecoveryCorrespondenceRequest(BaseModel):
    dispute_id:str|None=None;direction:str=Field(pattern="^(inbound|outbound)$");channel:str=Field(pattern="^(portal|email|mail|phone|edi)$");subject:str=Field(min_length=2,max_length=300);body:str=Field(min_length=2,max_length=10000);external_message_id:str|None=None;idempotency_key:str=Field(min_length=8,max_length=160)
class CloseRecoveryCaseRequest(BaseModel):
    reason_code:str=Field(min_length=3,max_length=100);rationale:str=Field(min_length=10,max_length=5000);expected_case_version:int=Field(ge=1);lease_token:str=Field(min_length=16);idempotency_key:str=Field(min_length=8,max_length=160)
