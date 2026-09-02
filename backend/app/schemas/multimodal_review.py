from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.domain.multimodal_review import ReviewAnnotationKind, ReviewAnnotationTarget


class MultimodalReviewAnnotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_type: ReviewAnnotationTarget
    target_id: str = Field(min_length=1, max_length=180)
    annotation_kind: ReviewAnnotationKind = ReviewAnnotationKind.NOTE
    anchor: dict[str, object] = Field(default_factory=dict)
    body: str = Field(min_length=1, max_length=10000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=180)


class MultimodalReviewAnnotationResponse(BaseModel):
    annotation_id: str
    reviewer_user_id: str
    target_type: str
    target_id: str
    annotation_kind: str
    anchor: dict[str, object]
    body: str
    tags: list[str]
    created_at: datetime


class EvidenceAccessResponse(BaseModel):
    evidence_id: str
    media_type: str
    document_type: str
    url: str
    expires_in_seconds: int
    content_sha256: str
