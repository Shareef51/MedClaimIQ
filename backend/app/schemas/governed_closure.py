from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from app.domain.claims import HumanDecision
from app.domain.governed_closure import SecondReviewAction
from app.domain.review_workbench import ReviewReasonCode


class PartialLineDecision(BaseModel):
    claim_line_id: str = Field(min_length=1, max_length=128)
    outcome: str = Field(pattern="^(approve|deny)$")
    amount: Decimal = Field(ge=0)
    reason_code: ReviewReasonCode


class DecisionPacketUpsertRequest(BaseModel):
    decision: HumanDecision
    rationale: str = Field(min_length=10, max_length=10000)
    reason_codes: list[ReviewReasonCode] = Field(min_length=1, max_length=12)
    evidence_snapshot_ids: list[str] = Field(min_length=1, max_length=200)
    finding_refs: list[str] = Field(default_factory=list, max_length=200)
    annotation_refs: list[str] = Field(default_factory=list, max_length=200)
    inconsistency_refs: list[str] = Field(default_factory=list, max_length=200)
    checkpoint_refs: list[str] = Field(default_factory=list, max_length=100)
    approved_amount: Decimal | None = Field(default=None, ge=0)
    partial_line_decisions: list[PartialLineDecision] = Field(default_factory=list, max_length=500)
    ai_disagreement_reason: str | None = Field(default=None, max_length=5000)
    escalation_queue: str | None = Field(default=None, min_length=2, max_length=100)
    expected_claim_status_version: int = Field(ge=1)
    expected_packet_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=8, max_length=180)


class DecisionPacketValidateRequest(BaseModel):
    expected_packet_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=180)


class SecondReviewRequest(BaseModel):
    action: SecondReviewAction
    rationale: str = Field(min_length=10, max_length=10000)
    expected_packet_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=180)


class DecisionCloseRequest(BaseModel):
    expected_packet_version: int = Field(ge=1)
    expected_claim_status_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=180)
