from datetime import date
from pydantic import BaseModel, Field

class ReportingPeriodCreateRequest(BaseModel):
    period_key:str=Field(min_length=3,max_length=50);report_type:str=Field(default="recovery_accounting_closeout",min_length=3,max_length=80);jurisdiction:str=Field(default="internal_control_reporting",min_length=3,max_length=80);start_date:date;end_date:date;accounting_period_ids:list[str]=Field(min_length=1,max_length=24);idempotency_key:str=Field(min_length=3,max_length=180)
class SubmissionPackageCreateRequest(BaseModel):
    correction_of_package_id:str|None=Field(default=None,max_length=128);amendment_reason:str|None=Field(default=None,max_length=2000);idempotency_key:str=Field(min_length=3,max_length=180)
class PackageLockRequest(BaseModel): expected_source_watermark_sha256:str=Field(min_length=64,max_length=64)
class CertificationRequest(BaseModel): rationale:str=Field(min_length=20,max_length=4000)
class SubmissionStageRequest(BaseModel): rationale:str=Field(min_length=20,max_length=4000)
class SubmissionReceiptRequest(BaseModel):
    external_submission_id:str=Field(min_length=3,max_length=180);submission_status:str=Field(pattern="^(accepted|received|accepted_with_warnings|rejected)$");external_receipt_reference:str=Field(min_length=3,max_length=240);receipt_metadata:dict=Field(default_factory=dict);idempotency_key:str=Field(min_length=3,max_length=180)
class AuditAnnotationRequest(BaseModel):
    annotation_type:str=Field(min_length=3,max_length=60);body:str=Field(min_length=10,max_length=6000);source_refs:list[str]=Field(default_factory=list,max_length=50);idempotency_key:str=Field(min_length=3,max_length=180)
