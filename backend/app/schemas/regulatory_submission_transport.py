from pydantic import BaseModel,Field
from typing import Any

class DestinationCreateRequest(BaseModel):
    destination_key:str;regulator_name:str;transport_type:str;endpoint_reference:str;schema_name:str;schema_version:str;registry_version:int=1
class SubmissionReleaseRequest(BaseModel):
    destination_id:str;schema_name:str;schema_version:str;release_reason:str=Field(min_length=12);idempotency_key:str
class AckRequest(BaseModel):
    destination_id:str;external_event_id:str;external_submission_reference:str;acknowledgment_status:str;receipt_payload:dict[str,Any]={};signature:str;rejection_code:str|None=None;rejection_reason:str|None=None
class RecoveryRequest(BaseModel):
    rationale:str=Field(min_length=12)
