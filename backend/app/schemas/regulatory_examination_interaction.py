from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
class MeetingCreate(BaseModel):
    examination_id:str; title:str; scheduled_at:str; agenda:list[str]=Field(default_factory=list); attendees:list[dict[str,Any]]=Field(default_factory=list)
class StatementCapture(BaseModel):
    meeting_id:str; speaker_type:str; text:str; classification:str; source_ref:str|None=None; transcript_timecode:str|None=None; evidence_refs:list[str]=Field(default_factory=list)
class CommitmentCandidateCreate(BaseModel):
    meeting_id:str; statement_id:str; description:str; proposed_owner_user_id:str|None=None; proposed_due_at:str|None=None; finding_ids:list[str]=Field(default_factory=list); evidence_request_ids:list[str]=Field(default_factory=list)
class CommitmentHumanDecision(BaseModel):
    decision:str; reviewer_role:str; rationale:str; owner_user_id:str|None=None; due_at:str|None=None
class ActionItemCreate(BaseModel):
    meeting_id:str; description:str; owner_user_id:str; due_at:str|None=None; finding_ids:list[str]=Field(default_factory=list)
class MeetingSummaryRequest(BaseModel):
    meeting_id:str; statements:list[dict[str,Any]]=Field(default_factory=list); prior_submissions:list[dict[str,Any]]=Field(default_factory=list)
