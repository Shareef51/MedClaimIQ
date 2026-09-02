from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FindingDisposition(StrEnum):
    SUPPORTED = "supported"
    MISMATCH = "mismatch"
    RISK = "risk"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REVIEW_REQUIRED = "review_required"


class RecommendationKind(StrEnum):
    SUPPORT_APPROVAL = "support_approval"
    SUPPORT_DENIAL = "support_denial"
    PENDING_DOCUMENTS = "pending_documents"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    NO_RECOMMENDATION = "no_recommendation"


class StructuredFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=1200)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_keys: list[str] = Field(default_factory=list, max_length=20)
    disposition: FindingDisposition
    risk_flags: list[str] = Field(default_factory=list, max_length=20)
    requires_human_review: bool = False

    @field_validator("evidence_keys", "risk_flags")
    @classmethod
    def unique_items(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class SpecialistAgentOutput(BaseModel):
    """Strict model output shared by all specialist agents.

    This schema intentionally has no final_decision, approve, deny, payment, or lifecycle
    mutation field. Decision-support is advisory and still subject to human review.
    """

    model_config = ConfigDict(extra="forbid")
    findings: list[StructuredFinding] = Field(default_factory=list, max_length=12)
    recommendation: RecommendationKind = RecommendationKind.NO_RECOMMENDATION
    rationale: str = Field(default="", max_length=1800)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = False
    missing_evidence: list[str] = Field(default_factory=list, max_length=12)


PROHIBITED_STRUCTURED_FIELDS = frozenset({
    "final_decision", "approve_claim", "deny_claim", "payment_action", "claim_status",
    "tenant_id", "claim_id", "sql", "tool_arguments", "execute_action",
})
