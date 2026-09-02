from __future__ import annotations
from pydantic import BaseModel, Field


class AppealSnapshotBuildRequest(BaseModel):
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealReingestRequest(BaseModel):
    evidence_id: str = Field(min_length=1,max_length=128)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealRAGSearchRequest(BaseModel):
    query: str = Field(min_length=3,max_length=4000)
    top_k: int = Field(default=12,ge=1,le=30)


class AppealAgentRunRequest(BaseModel):
    query: str = Field(default="What supplemental evidence materially changes, contradicts, or corroborates the original claim decision evidence?",min_length=3,max_length=4000)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealAnnotationRequest(BaseModel):
    target_type: str = Field(pattern="^(evidence|comparison|rag_item|recommendation|checkpoint)$")
    target_id: str = Field(min_length=1,max_length=180)
    body: str = Field(min_length=3,max_length=10000)
    anchor: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list,max_length=20)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealMissingEvidenceRequest(BaseModel):
    document_types: list[str] = Field(min_length=1,max_length=20)
    rationale: str = Field(min_length=10,max_length=5000)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealEscalationRequest(BaseModel):
    reason: str = Field(min_length=10,max_length=5000)
    assigned_queue: str = Field(default="appeal_second_level",min_length=3,max_length=80)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealCheckpointResumeRequest(BaseModel):
    idempotency_key: str = Field(min_length=8,max_length=180)
