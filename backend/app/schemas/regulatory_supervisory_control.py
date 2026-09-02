from datetime import date
from pydantic import BaseModel, Field
from typing import Any

class CaseRefreshRequest(BaseModel):
    transmission_id:str|None=None
class RejectionRootCauseRequest(BaseModel):
    root_cause:str
    rationale:str=Field(min_length=12)
    expected_case_version:int
class AmendmentEffectivenessRequest(BaseModel):
    effectiveness:str
    rationale:str=Field(min_length=12)
    expected_case_version:int
class AttestationPrepareRequest(BaseModel):
    expected_case_version:int
class CertificationRequest(BaseModel):
    conclusion:str="reconciled"
    rationale:str=Field(min_length=12)
    expected_case_version:int
class ExceptionResolutionRequest(BaseModel):
    rationale:str=Field(min_length=12)
class AnnotationRequest(BaseModel):
    annotation_type:str
    body:str=Field(min_length=3)
    source_refs:list[dict[str,Any]]=[]
    idempotency_key:str
class CorrespondenceRequest(BaseModel):
    direction:str
    channel:str
    subject:str
    body:str=Field(min_length=3)
    external_reference:str|None=None
    idempotency_key:str
class CalendarDeadlineRequest(BaseModel):
    destination_id:str
    deadline_key:str
    due_date:date
    description:str=Field(min_length=5)
class AuditExportRequest(BaseModel):
    include_correspondence:bool=True
