from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from app.domain.financial_handoff import SettlementStatus
class FinancialPacketPrepareRequest(BaseModel): expected_packet_version:int|None=Field(default=None,ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class FinancialPacketLockRequest(BaseModel): expected_packet_version:int=Field(ge=1); idempotency_key:str=Field(min_length=8,max_length=180)
class FinancialPacketAuthorizeRequest(BaseModel): rationale:str=Field(min_length=20,max_length=5000); idempotency_key:str=Field(min_length=8,max_length=180)
class PaymentIntentStageRequest(BaseModel): payee_ref:str=Field(min_length=2,max_length=160); idempotency_key:str=Field(min_length=8,max_length=180)
class PaymentHandoffRequest(BaseModel): adapter_name:str="sandbox-financial-ledger"; idempotency_key:str=Field(min_length=8,max_length=180)
class PaymentHoldRequest(BaseModel): hold_type:str=Field(min_length=2,max_length=60); reason_code:str=Field(min_length=2,max_length=100); rationale:str=Field(min_length=20,max_length=5000); idempotency_key:str=Field(min_length=8,max_length=180)
class HoldReleaseRequest(BaseModel): rationale:str=Field(min_length=20,max_length=5000); idempotency_key:str=Field(min_length=8,max_length=180)
class SettlementIngestRequest(BaseModel): provider_event_id:str=Field(min_length=4,max_length=180); status:SettlementStatus; settled_amount:Decimal|None=None; currency:str|None=Field(default=None,min_length=3,max_length=3); external_reference:str|None=Field(default=None,max_length=180); payload:dict={}
class VoidReissueRequest(BaseModel): action:str; reason:str=Field(min_length=20,max_length=5000); idempotency_key:str=Field(min_length=8,max_length=180)
class VoidReissueApproveRequest(BaseModel): idempotency_key:str=Field(min_length=8,max_length=180)
