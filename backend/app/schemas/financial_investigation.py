from decimal import Decimal
from pydantic import BaseModel, Field

class CreateInvestigationCaseRequest(BaseModel):
    investigation_id:str=Field(min_length=3,max_length=128)
    idempotency_key:str=Field(min_length=8,max_length=128)
class AcquireInvestigationLeaseRequest(BaseModel):
    expected_case_version:int=Field(ge=1)
    lease_minutes:int=Field(default=30,ge=5,le=120)
class InvestigationAnnotationRequest(BaseModel):
    target_type:str=Field(min_length=2,max_length=60)
    target_id:str=Field(min_length=2,max_length=128)
    body:str=Field(min_length=3,max_length=6000)
    tags:list[str]=Field(default_factory=list,max_length=20)
    idempotency_key:str=Field(min_length=8,max_length=128)
class RootCauseRequest(BaseModel):
    root_cause_code:str=Field(min_length=3,max_length=80)
    rationale:str=Field(min_length=12,max_length=6000)
    ai_disagreement_rationale:str|None=Field(default=None,max_length=6000)
    expected_case_version:int=Field(ge=1)
    lease_token:str=Field(min_length=16,max_length=256)
class RemediationProposalRequest(BaseModel):
    remediation_type:str=Field(min_length=3,max_length=80)
    amount:Decimal=Field(default=Decimal("0"),ge=0)
    currency:str=Field(default="USD",min_length=3,max_length=3)
    reason_code:str=Field(min_length=3,max_length=100)
    rationale:str=Field(min_length=12,max_length=6000)
    idempotency_key:str=Field(min_length=8,max_length=128)
    lease_token:str=Field(min_length=16,max_length=256)
class RemediationApprovalRequest(BaseModel):
    rationale:str=Field(min_length=12,max_length=6000)
    idempotency_key:str=Field(min_length=8,max_length=128)
class CaseClosureRequest(BaseModel):
    reason_code:str=Field(min_length=3,max_length=100)
    rationale:str=Field(min_length=12,max_length=6000)
    expected_case_version:int=Field(ge=1)
    lease_token:str=Field(min_length=16,max_length=256)
    idempotency_key:str=Field(min_length=8,max_length=128)
