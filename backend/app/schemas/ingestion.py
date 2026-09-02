from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.ingestion import MediaKind, UploadSessionStatus


class UploadInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_filename: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=2, max_length=80)
    declared_media_type: str = Field(min_length=3, max_length=160)
    expected_byte_size: int = Field(gt=0)
    expected_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    captured_at: datetime | None = None

    @field_validator("client_filename")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("filename may not contain control characters")
        return value


class UploadInitiateResponse(BaseModel):
    upload_session_id: str
    claim_id: str
    status: UploadSessionStatus
    method: str
    upload_url: str
    required_headers: dict[str, str]
    form_fields: dict[str, str]
    upload_expires_at: datetime
    expected_byte_size: int
    media_kind: MediaKind


class UploadCompleteResponse(BaseModel):
    upload_session_id: str
    claim_id: str
    status: UploadSessionStatus
    accepted_for_processing: bool
    event_id: str


class UploadSessionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_session_id: str
    claim_id: str
    initiated_by_user_id: str
    document_type: str
    declared_media_type: str
    detected_media_type: str | None
    media_kind: str
    expected_byte_size: int
    actual_byte_size: int | None
    actual_sha256: str | None
    status: str
    status_version: int
    rejection_code: str | None
    evidence_id: str | None
    upload_expires_at: datetime
    uploaded_at: datetime | None
    verified_at: datetime | None
    finalized_at: datetime | None
    media_metadata: dict[str, object]


class IngestionModelResponse(BaseModel):
    storage_boundary: tuple[str, ...]
    validation_controls: tuple[str, ...]
    malware_controls: tuple[str, ...]
    event_controls: tuple[str, ...]
    supported_media_kinds: tuple[MediaKind, ...]
    acceptance_rule: str
