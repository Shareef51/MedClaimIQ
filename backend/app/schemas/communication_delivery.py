from __future__ import annotations
from pydantic import BaseModel, Field
from app.domain.communication_delivery import CommunicationChannel, ConsentStatus


class EndpointUpsertRequest(BaseModel):
    audience: str = Field(pattern="^(patient|provider|authorized_representative)$")
    channel: CommunicationChannel
    destination: str = Field(min_length=3,max_length=320)
    consent_status: ConsentStatus = ConsentStatus.REQUIRED_ONLY
    locale: str = Field(default="en",pattern="^(en|es|ar)$")
    accessibility_preferences: dict = Field(default_factory=dict)


class TemplateCreateRequest(BaseModel):
    template_key: str = Field(min_length=3,max_length=100)
    template_version: str = Field(min_length=1,max_length=40)
    locale: str = Field(pattern="^(en|es|ar)$")
    channel: CommunicationChannel
    subject_template: str | None = Field(default=None,max_length=500)
    body_template: str = Field(min_length=20,max_length=20000)
    accessibility_schema: dict = Field(default_factory=dict)
    change_reason: str = Field(min_length=10,max_length=5000)


class TemplateApproveRequest(BaseModel):
    approval_reason: str = Field(min_length=10,max_length=5000)


class QueueNoticeRequest(BaseModel):
    idempotency_key: str = Field(min_length=8,max_length=180)


class WorkerLeaseRequest(BaseModel):
    worker_id: str = Field(min_length=3,max_length=128)
    limit: int = Field(default=20,ge=1,le=100)


class WorkerExecuteRequest(BaseModel):
    worker_id: str = Field(min_length=3,max_length=128)


class WebhookReceiptRequest(BaseModel):
    tenant_id: str = Field(min_length=1,max_length=64)
    dispatch_id: str = Field(min_length=1,max_length=128)
    provider_event_id: str = Field(min_length=1,max_length=180)
    provider_message_id: str | None = Field(default=None,max_length=180)
    status: str = Field(pattern="^(accepted|delivered|bounced|failed|complaint)$")
    occurred_at: str | None = None


class LegalHoldCreateRequest(BaseModel):
    reason: str = Field(min_length=10,max_length=5000)


class LegalHoldReleaseRequest(BaseModel):
    release_reason: str = Field(min_length=10,max_length=5000)


class RecoveryRequest(BaseModel):
    reason: str = Field(min_length=10,max_length=5000)


class ReconcileRequest(BaseModel):
    idempotency_key: str = Field(min_length=8,max_length=180)
