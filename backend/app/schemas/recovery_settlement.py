from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel,Field
class SettlementEvidenceRequest(BaseModel):
    evidence_type:str;amount:Decimal=Field(ge=0);currency:str=Field(min_length=3,max_length=3);installment_sequence:int=Field(ge=1);external_reference:str=Field(min_length=3,max_length=180);bank_reference:str|None=None;remittance_reference:str|None=None;provider_reference:str|None=None;evidence_refs:list[str]=Field(default_factory=list);occurred_at:datetime|None=None;idempotency_key:str
class SettlementEvidenceVerificationRequest(BaseModel):
    reference_match:bool;verification_rationale:str=Field(min_length=20);expected_case_version:int;idempotency_key:str
class SettlementLedgerCorrelationRequest(BaseModel):
    journal_id:str;amount:Decimal=Field(gt=0);currency:str=Field(min_length=3,max_length=3);idempotency_key:str
class SettlementCorrespondenceRequest(BaseModel):
    direction:str;channel:str;subject:str=Field(min_length=3);body:str=Field(min_length=10);external_message_id:str|None=None;idempotency_key:str
class SettlementCertificatePrepareRequest(BaseModel):
    accounting_period_id:str;reason_codes:list[str]=Field(min_length=1);rationale:str=Field(min_length=30);expected_case_version:int;idempotency_key:str
class SettlementCertificateDecisionRequest(BaseModel):
    action:str=Field(pattern="^(approve|reject)$");rationale:str=Field(min_length=30);expected_case_version:int;idempotency_key:str
class SettlementExceptionResolveRequest(BaseModel):
    rationale:str=Field(min_length=20);expected_case_version:int;idempotency_key:str
