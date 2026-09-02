from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.domain.claims import HumanDecision
from app.domain.review_workbench import ReviewNoteType, ReviewReasonCode


class ReviewLockRequest(BaseModel):
    lease_seconds: int = Field(default=300, ge=60, le=1800)

class ReviewLockResponse(BaseModel):
    lock_id: str; lock_token: str; lock_version: int; locked_until: datetime

class ReviewerNoteCreate(BaseModel):
    note_type: ReviewNoteType = ReviewNoteType.GENERAL
    body: str = Field(min_length=1, max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=180)

class ReviewEvidenceRequest(BaseModel):
    rationale: str = Field(min_length=5, max_length=5000)
    requested_document_types: list[str] = Field(min_length=1, max_length=25)
    evidence_snapshot_ids: list[str] = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=160)

class ReviewDecisionRequest(BaseModel):
    decision: HumanDecision
    rationale: str = Field(min_length=5, max_length=10000)
    reason_codes: list[ReviewReasonCode] = Field(min_length=1, max_length=10)
    evidence_snapshot_ids: list[str] = Field(min_length=1, max_length=100)
    expected_claim_status_version: int = Field(ge=1)
    override_reason: str | None = Field(default=None, max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=160)

class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    work_item_id: str; claim_id: str; status: str; priority_score: int; priority_band: str
    priority_reasons: list[str]; assigned_reviewer_user_id: str | None; sla_due_at: datetime | None
