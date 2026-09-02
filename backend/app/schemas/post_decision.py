from __future__ import annotations
from pydantic import BaseModel, Field
from app.domain.claims import HumanDecision
from app.domain.post_decision import AppealResolutionOutcome


class DecisionNoticeCreateRequest(BaseModel):
    packet_id: str = Field(min_length=1,max_length=128)
    audience: str = Field(default="patient",pattern="^(patient|provider|authorized_representative)$")
    idempotency_key: str = Field(min_length=8,max_length=180)


class DecisionNoticeReleaseRequest(BaseModel):
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealCreateRequest(BaseModel):
    notice_id: str = Field(min_length=1,max_length=128)
    grounds: list[str] = Field(min_length=1,max_length=12)
    statement: str = Field(min_length=10,max_length=10000)
    late_filing_reason: str | None = Field(default=None,max_length=5000)
    idempotency_key: str = Field(min_length=8,max_length=180)


class SupplementalEvidenceLinkRequest(BaseModel):
    evidence_id: str = Field(min_length=1,max_length=128)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealAssignRequest(BaseModel):
    reviewer_user_id: str = Field(min_length=1,max_length=128)
    assignment_reason: str = Field(min_length=10,max_length=5000)
    expected_appeal_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealReopenRequest(BaseModel):
    expected_appeal_version: int = Field(ge=1)
    rationale: str = Field(min_length=10,max_length=5000)
    idempotency_key: str = Field(min_length=8,max_length=180)


class AppealResolveRequest(BaseModel):
    outcome: AppealResolutionOutcome
    controlling_decision: HumanDecision
    reason_codes: list[str] = Field(min_length=1,max_length=12)
    rationale: str = Field(min_length=10,max_length=10000)
    expected_appeal_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8,max_length=180)


class CorrespondenceCreateRequest(BaseModel):
    appeal_id: str | None = Field(default=None,max_length=128)
    notice_id: str | None = Field(default=None,max_length=128)
    direction: str = Field(pattern="^(inbound|outbound)$")
    channel: str = Field(pattern="^(portal|email|mail|sms|fax|api)$")
    audience: str = Field(min_length=2,max_length=60)
    external_message_id: str | None = Field(default=None,max_length=160)
    payload_sha256: str = Field(min_length=64,max_length=64)
    idempotency_key: str = Field(min_length=8,max_length=180)


class DeliveryAttemptRequest(BaseModel):
    channel: str = Field(pattern="^(portal|email|mail|sms|fax|api)$")
    success: bool
    provider_message_id: str | None = Field(default=None,max_length=160)
    error_code: str | None = Field(default=None,max_length=80)
    error_detail: str | None = Field(default=None,max_length=5000)
