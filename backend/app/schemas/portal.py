from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.ingestion import UploadInitiateRequest, UploadInitiateResponse

class PortalClaimListItem(BaseModel):
    claim_id: str
    external_claim_ref: str
    status: str
    total_amount: str
    currency: str
    service_from: date
    service_to: date | None
    outstanding_request_count: int
    next_deadline_at: datetime | None

class PortalDocumentRequestView(BaseModel):
    request_id: str
    requested_document_types: list[str]
    instructions: str
    status: str
    due_at: datetime | None
    created_at: datetime

class PortalSubmissionView(BaseModel):
    submission_id: str
    request_id: str
    document_type: str
    status: str
    acknowledgement_code: str
    upload_session_id: str
    evidence_id: str | None
    created_at: datetime
    received_at: datetime | None

class PortalClaimView(BaseModel):
    claim_id: str
    external_claim_ref: str
    status: str
    status_label: str
    total_amount: str
    currency: str
    service_from: date
    service_to: date | None
    document_requests: list[PortalDocumentRequestView]
    submissions: list[PortalSubmissionView]
    verification: dict[str, object]
    deadlines: list[dict[str, object]]
    safe_timeline: list[dict[str, object]]
    privacy_notice: str

class PortalUploadInitiateRequest(UploadInitiateRequest):
    model_config = ConfigDict(extra="forbid")

class PortalUploadInitiateResponse(BaseModel):
    submission_id: str
    acknowledgement_code: str
    upload: UploadInitiateResponse

class PortalUploadCompleteResponse(BaseModel):
    submission_id: str
    acknowledgement_code: str
    status: str
    accepted_for_security_processing: bool
    event_id: str

class PortalModelResponse(BaseModel):
    allowed_roles: tuple[str, ...]
    visible_sections: tuple[str, ...]
    hidden_internal_sections: tuple[str, ...]
    upload_rule: str
    realtime_rule: str
