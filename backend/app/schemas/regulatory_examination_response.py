from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class ExaminerQuestionCreate(BaseModel):
    examination_id:str; external_question_ref:str; question_text:str; due_at:str|None=None; parent_question_id:str|None=None; owner_user_id:str|None=None
class EvidenceRefreshRequest(BaseModel):
    question_id:str; evidence:list[dict[str,Any]]=Field(default_factory=list); current_versions:dict[str,str]=Field(default_factory=dict)
class ResponseRevisionCreate(BaseModel):
    question_id:str; text:str; evidence_refs:list[str]=Field(default_factory=list); prior_response_ids:list[str]=Field(default_factory=list); amendment_reason:str|None=None
class HumanReviewDecision(BaseModel):
    decision:str; role:str; rationale:str
class SubmissionRecordRequest(BaseModel):
    revision_id:str; authorized_channel:str; human_approved:bool=True; external_submission_ref:str|None=None
class ReceiptRecordRequest(BaseModel):
    submission_id:str; status:str; regulator_reference:str|None=None; received_at:str|None=None; notes:str|None=None
class FollowUpCreate(BaseModel):
    submission_id:str; external_question_ref:str; question_text:str; due_at:str|None=None
