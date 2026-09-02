from __future__ import annotations

from enum import StrEnum


class ClaimStatus(StrEnum):
    SUBMITTED = "submitted"
    QUARANTINED = "quarantined"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    VERIFYING = "verifying"
    PENDING_EVIDENCE = "pending_evidence"
    AI_REVIEWED = "ai_reviewed"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    APPEAL_READY = "appeal_ready"
    REJECTED_AT_INGESTION = "rejected_at_ingestion"
    PROCESSING_FAILED = "processing_failed"
    CANCELLED = "cancelled"


class EvidenceStatus(StrEnum):
    QUARANTINED = "quarantined"
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    READY = "ready"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceSourceType(StrEnum):
    USER_UPLOAD = "user_upload"
    PROVIDER_UPLOAD = "provider_upload"
    HOSPITAL_SYSTEM = "hospital_system"
    FHIR = "fhir"
    PAYER_SYSTEM = "payer_system"
    GENERATED_DERIVATIVE = "generated_derivative"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class EvidenceRelationship(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"


class HumanDecision(StrEnum):
    APPROVE = "approve"
    DENY = "deny"
    PARTIAL_APPROVE = "partial_approve"
    REQUEST_INFORMATION = "request_information"
    ESCALATE = "escalate"


class ActorType(StrEnum):
    HUMAN = "human"
    SYSTEM = "system"
    AGENT = "agent"
    WORKER = "worker"


# Canonical lifecycle. Failures/cancellation are intentionally reachable from active
# processing states, while a final human action is required before COMPLETED.
ALLOWED_CLAIM_TRANSITIONS: dict[ClaimStatus, frozenset[ClaimStatus]] = {
    ClaimStatus.SUBMITTED: frozenset(
        {ClaimStatus.QUARANTINED, ClaimStatus.CANCELLED, ClaimStatus.REJECTED_AT_INGESTION}
    ),
    ClaimStatus.QUARANTINED: frozenset(
        {ClaimStatus.EXTRACTING, ClaimStatus.REJECTED_AT_INGESTION, ClaimStatus.CANCELLED}
    ),
    ClaimStatus.EXTRACTING: frozenset(
        {ClaimStatus.NORMALIZING, ClaimStatus.PROCESSING_FAILED, ClaimStatus.CANCELLED}
    ),
    ClaimStatus.NORMALIZING: frozenset(
        {ClaimStatus.VERIFYING, ClaimStatus.PROCESSING_FAILED, ClaimStatus.CANCELLED}
    ),
    ClaimStatus.VERIFYING: frozenset(
        {
            ClaimStatus.PENDING_EVIDENCE,
            ClaimStatus.AI_REVIEWED,
            ClaimStatus.PROCESSING_FAILED,
            ClaimStatus.CANCELLED,
        }
    ),
    ClaimStatus.PENDING_EVIDENCE: frozenset(
        {ClaimStatus.VERIFYING, ClaimStatus.CANCELLED, ClaimStatus.PROCESSING_FAILED}
    ),
    ClaimStatus.AI_REVIEWED: frozenset({ClaimStatus.HUMAN_REVIEW, ClaimStatus.CANCELLED}),
    ClaimStatus.HUMAN_REVIEW: frozenset(
        {ClaimStatus.PENDING_EVIDENCE, ClaimStatus.COMPLETED, ClaimStatus.APPEAL_READY}
    ),
    ClaimStatus.PROCESSING_FAILED: frozenset(
        {ClaimStatus.QUARANTINED, ClaimStatus.EXTRACTING, ClaimStatus.CANCELLED}
    ),
    ClaimStatus.COMPLETED: frozenset({ClaimStatus.APPEAL_READY}),
    ClaimStatus.APPEAL_READY: frozenset(),
    ClaimStatus.REJECTED_AT_INGESTION: frozenset(),
    ClaimStatus.CANCELLED: frozenset(),
}


def can_transition(from_status: ClaimStatus, to_status: ClaimStatus) -> bool:
    return to_status in ALLOWED_CLAIM_TRANSITIONS[from_status]
