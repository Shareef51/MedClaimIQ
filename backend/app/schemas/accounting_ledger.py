from decimal import Decimal
from pydantic import BaseModel,Field
class ERAIngestRequest(BaseModel):era_reference:str=Field(min_length=3,max_length=180);payment_reference:str=Field(min_length=3,max_length=180);provider_ref:str=Field(min_length=2,max_length=160);paid_amount:Decimal=Field(gt=0);currency:str=Field(default="USD",min_length=3,max_length=3);remittance_payload:dict={}
class EFTIngestRequest(BaseModel):eft_reference:str=Field(min_length=3,max_length=180);bank_reference:str=Field(min_length=3,max_length=180);trace_number:str=Field(min_length=3,max_length=180);amount:Decimal=Field(gt=0);currency:str=Field(default="USD",min_length=3,max_length=3);status:str=Field(default="posted",min_length=2,max_length=30)
class ReconcileRequest(BaseModel):idempotency_key:str=Field(min_length=8,max_length=180)
class ReturnedPaymentRequest(BaseModel):return_reference:str=Field(min_length=3,max_length=180);return_code:str=Field(min_length=2,max_length=80);amount:Decimal=Field(gt=0);currency:str=Field(default="USD",min_length=3,max_length=3);reason:str=Field(min_length=20,max_length=5000)
class AdjustmentRequest(BaseModel):adjustment_type:str;amount:Decimal=Field(gt=0);reason_code:str=Field(min_length=2,max_length=80);rationale:str=Field(min_length=20,max_length=5000);idempotency_key:str=Field(min_length=8,max_length=180)
class AdjustmentApproveRequest(BaseModel):rationale:str=Field(min_length=20,max_length=5000);idempotency_key:str=Field(min_length=8,max_length=180)
class PeriodCloseRequest(BaseModel):expected_lock_version:int=Field(ge=1);rationale:str=Field(min_length=20,max_length=5000);idempotency_key:str=Field(min_length=8,max_length=180)
