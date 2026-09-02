from decimal import Decimal
from pydantic import BaseModel,Field
class ProviderDisputeDecisionPacketRequest(BaseModel):
    outcome:str;amended_target_amount:Decimal=Field(ge=0);rationale:str=Field(min_length=20,max_length=12000);reason_codes:list[str]=Field(min_length=1,max_length=20);citation_refs:list[str]=Field(min_length=1,max_length=100);resolved_comparison_refs:list[str]=Field(default_factory=list,max_length=100);checkpoint_refs:list[str]=Field(default_factory=list,max_length=100);recommendation_disagreement_reason:str|None=Field(default=None,max_length=5000);expected_case_version:int=Field(ge=1);expected_packet_version:int|None=Field(default=None,ge=1);idempotency_key:str=Field(min_length=8,max_length=180)
class ProviderDisputePacketLockRequest(BaseModel):expected_packet_version:int=Field(ge=1);idempotency_key:str=Field(min_length=8,max_length=180)
class ProviderDisputeSecondReviewRequest(BaseModel):action:str;rationale:str=Field(min_length=20,max_length=5000);expected_packet_version:int=Field(ge=1);idempotency_key:str=Field(min_length=8,max_length=180)
class ProviderDisputeFinalCloseRequest(BaseModel):expected_packet_version:int=Field(ge=1);expected_case_version:int=Field(ge=1);idempotency_key:str=Field(min_length=8,max_length=180)

class ProviderDisputeReconciliationVerificationRequest(BaseModel):
    status:str;external_reference:str=Field(min_length=3,max_length=180);expected_case_version:int=Field(ge=1);lease_token:str=Field(min_length=20,max_length=256);idempotency_key:str=Field(min_length=8,max_length=180)
class ProviderDisputeFinalRecoveryCloseRequest(BaseModel):
    rationale:str=Field(min_length=20,max_length=5000);expected_case_version:int=Field(ge=1);lease_token:str=Field(min_length=20,max_length=256);idempotency_key:str=Field(min_length=8,max_length=180)
