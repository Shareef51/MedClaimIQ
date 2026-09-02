from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.claims import (
    ActorType,
    ClaimStatus,
    EvidenceRelationship,
    EvidenceSourceType,
    EvidenceStatus,
    HumanDecision,
)


class PatientCreate(BaseModel):
    patient_id: str = Field(min_length=3, max_length=128)
    patient_subject_id: str = Field(min_length=3, max_length=128)
    external_identifiers: dict[str, str] = Field(default_factory=dict)
    synthetic_data: bool = True


class ProviderCreate(BaseModel):
    provider_id: str = Field(min_length=3, max_length=128)
    organization_id: str = Field(min_length=3, max_length=128)
    provider_ref: str = Field(min_length=1, max_length=160)
    provider_type: str = Field(default="organization", min_length=2, max_length=60)
    external_identifiers: dict[str, str] = Field(default_factory=dict)


class PolicyCreate(BaseModel):
    policy_id: str = Field(min_length=3, max_length=128)
    patient_subject_id: str = Field(min_length=3, max_length=128)
    payer_organization_id: str = Field(min_length=3, max_length=128)
    policy_ref: str = Field(min_length=1, max_length=160)
    plan_name: str = Field(min_length=2, max_length=180)
    effective_from: date
    effective_to: date | None = None
    policy_version: int = Field(default=1, ge=1)
    source_system: str = Field(default="synthetic", min_length=2, max_length=120)

    @model_validator(mode="after")
    def validate_dates(self) -> "PolicyCreate":
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class EncounterCreate(BaseModel):
    encounter_id: str = Field(min_length=3, max_length=128)
    patient_subject_id: str = Field(min_length=3, max_length=128)
    provider_organization_id: str = Field(min_length=3, max_length=128)
    encounter_ref: str = Field(min_length=1, max_length=160)
    encounter_type: str = Field(min_length=2, max_length=80)
    started_at: datetime
    ended_at: datetime | None = None
    source_system: str = Field(default="synthetic", min_length=2, max_length=120)
    external_identifiers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_times(self) -> "EncounterCreate":
        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError("ended_at must be on or after started_at")
        return self


class ClaimCreate(BaseModel):
    claim_id: str = Field(min_length=3, max_length=128)
    external_claim_ref: str = Field(min_length=1, max_length=160)
    patient_subject_id: str = Field(min_length=3, max_length=128)
    provider_organization_id: str = Field(min_length=3, max_length=128)
    payer_organization_id: str = Field(min_length=3, max_length=128)
    policy_id: str | None = Field(default=None, max_length=128)
    encounter_id: str | None = Field(default=None, max_length=128)
    claim_type: str = Field(default="medical", min_length=2, max_length=60)
    assigned_reviewer_user_id: str | None = Field(default=None, max_length=128)
    total_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    service_from: date
    service_to: date | None = None
    created_by_actor_type: ActorType = ActorType.SYSTEM
    created_by_actor_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=160)
    trace_id: str | None = Field(default=None, max_length=128)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_service_window(self) -> "ClaimCreate":
        if self.service_to and self.service_to < self.service_from:
            raise ValueError("service_to must be on or after service_from")
        return self


class ClaimLineCreate(BaseModel):
    claim_line_id: str = Field(min_length=3, max_length=128)
    line_number: int = Field(gt=0)
    code_system: str = Field(min_length=2, max_length=40)
    service_code: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    service_date: date
    units: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    provider_id: str | None = Field(default=None, max_length=128)


class EvidenceCreate(BaseModel):
    evidence_id: str = Field(min_length=3, max_length=128)
    claim_id: str = Field(min_length=3, max_length=128)
    source_type: EvidenceSourceType
    source_system: str = Field(min_length=2, max_length=120)
    source_locator: dict[str, object] = Field(default_factory=dict)
    document_type: str = Field(min_length=2, max_length=80)
    media_type: str = Field(min_length=3, max_length=160)
    object_key: str = Field(min_length=3, max_length=1024)
    storage_etag: str | None = Field(default=None, max_length=160)
    storage_version_id: str | None = Field(default=None, max_length=256)
    content_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    byte_size: int = Field(ge=0)
    status: EvidenceStatus = EvidenceStatus.QUARANTINED
    evidence_version: int = Field(default=1, ge=1)
    uploaded_by_user_id: str | None = Field(default=None, max_length=128)
    captured_at: datetime | None = None
    authoritative: bool = False
    media_metadata: dict[str, object] = Field(default_factory=dict)
    verified_at: datetime | None = None
    actor_type: ActorType = ActorType.SYSTEM
    actor_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=160)
    trace_id: str | None = Field(default=None, max_length=128)


class EvidenceLineageCreate(BaseModel):
    lineage_id: str = Field(min_length=3, max_length=128)
    child_evidence_id: str = Field(min_length=3, max_length=128)
    parent_evidence_id: str = Field(min_length=3, max_length=128)
    relationship: EvidenceRelationship = EvidenceRelationship.DERIVED_FROM
    transformation_name: str | None = Field(default=None, max_length=120)
    transformation_version: str | None = Field(default=None, max_length=80)
    transformation_metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def prevent_self_edge(self) -> "EvidenceLineageCreate":
        if self.child_evidence_id == self.parent_evidence_id:
            raise ValueError("evidence cannot derive from itself")
        return self


class ClaimTransitionRequest(BaseModel):
    status_event_id: str = Field(min_length=3, max_length=128)
    to_status: ClaimStatus
    actor_type: ActorType
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)
    trace_id: str | None = Field(default=None, max_length=128)
    expected_status_version: int | None = Field(default=None, ge=1)


class HumanDecisionCreate(BaseModel):
    decision_id: str = Field(min_length=3, max_length=128)
    reviewer_user_id: str = Field(min_length=3, max_length=128)
    decision: HumanDecision
    rationale: str = Field(min_length=5, max_length=10000)
    evidence_snapshot: list[dict[str, object]] = Field(min_length=1)
    idempotency_key: str = Field(min_length=8, max_length=160)
    trace_id: str | None = Field(default=None, max_length=128)


class ClaimView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: str
    tenant_id: str
    external_claim_ref: str
    patient_subject_id: str
    provider_organization_id: str
    payer_organization_id: str
    policy_id: str | None
    encounter_id: str | None
    status: str
    status_version: int
    assigned_reviewer_user_id: str | None
    total_amount: Decimal
    currency: str
    service_from: date
    service_to: date | None


class ClaimDomainModelResponse(BaseModel):
    persisted_entities: tuple[str, ...]
    lifecycle_controls: tuple[str, ...]
    provenance_controls: tuple[str, ...]
    database_isolation: tuple[str, ...]
    final_decision_boundary: str
