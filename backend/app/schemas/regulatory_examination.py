from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any
class ExaminationOpenRequest(BaseModel):
    supervisory_case_id:str;external_inquiry_reference:str;inquiry_type:str;question_classification:str;inquiry_summary:str=Field(min_length=12);response_due_at:datetime
class DocumentRequestCreate(BaseModel):
    request_code:str;description:str=Field(min_length=5);due_at:datetime;requested_refs:list[dict[str,Any]]=Field(default_factory=list)
class DocumentRequestSatisfy(BaseModel):
    satisfied_refs:list[dict[str,Any]];expected_case_version:int
class EvidencePackRequest(BaseModel):expected_case_version:int
class EvidenceSearchRequest(BaseModel):query:str=Field(min_length=2);top_k:int=Field(default=8,ge=1,le=25)
class ResponseDraftRequest(BaseModel):
    response_text:str|None=None;cited_refs:list[dict[str,Any]]=Field(default_factory=list);use_ai_assistance:bool=False;idempotency_key:str;expected_case_version:int
class ResponseApprovalRequest(BaseModel):approval_rationale:str=Field(min_length=12);expected_case_version:int
class ResponseDeliveryRequest(BaseModel):
    channel:str="regulator_portal";subject:str;external_reference:str|None=None;supplemental_submission_reference:str|None=None;idempotency_key:str;expected_case_version:int
class FindingRequest(BaseModel):
    finding_code:str;severity:str;material:bool=False;description:str=Field(min_length=5);source_refs:list[dict[str,Any]]=Field(default_factory=list)
class FindingResolveRequest(BaseModel):rationale:str=Field(min_length=8);expected_case_version:int
class CommitmentRequest(BaseModel):
    commitment_key:str;description:str=Field(min_length=5);due_at:datetime;owner_user_id:str;evidence_refs:list[dict[str,Any]]=Field(default_factory=list)
class CommitmentCompleteRequest(BaseModel):evidence_refs:list[dict[str,Any]];expected_case_version:int
class CloseExaminationRequest(BaseModel):closure_rationale:str=Field(min_length=12);expected_case_version:int
class AIResponseDraft(BaseModel):
    response_text:str=Field(min_length=20)
    cited_refs:list[dict[str,Any]]
    uncertainties:list[str]=Field(default_factory=list)
