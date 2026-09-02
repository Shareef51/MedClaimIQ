from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ReviewWorkStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    WAITING_EVIDENCE = "waiting_evidence"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ReviewPriorityBand(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewNoteType(StrEnum):
    GENERAL = "general"
    EVIDENCE = "evidence"
    ESCALATION = "escalation"
    DECISION = "decision"


class ReviewReasonCode(StrEnum):
    EVIDENCE_SUPPORTS = "evidence_supports"
    EVIDENCE_CONTRADICTS = "evidence_contradicts"
    POLICY_COVERAGE = "policy_coverage"
    CODING_ISSUE = "coding_issue"
    DUPLICATE_RISK = "duplicate_risk"
    FRAUD_WASTE_SIGNAL = "fraud_waste_signal"
    MISSING_DOCUMENTS = "missing_documents"
    HUMAN_JUDGMENT = "human_judgment"
    OTHER = "other"


class ReviewPriorityInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_status: str
    overdue_timers: int = 0
    critical_sla_items: int = 0
    high_sla_items: int = 0
    guardrail_escalations: int = 0
    waiting_human_checkpoints: int = 0
    material_contradictions: int = 0
    claim_amount: float = 0.0


def calculate_priority(inputs: ReviewPriorityInputs) -> tuple[int, ReviewPriorityBand, list[str]]:
    score = 10
    reasons: list[str] = []
    if inputs.claim_status == "human_review":
        score += 25; reasons.append("human_review")
    elif inputs.claim_status == "ai_reviewed":
        score += 15; reasons.append("ai_reviewed")
    if inputs.overdue_timers:
        score += min(30, inputs.overdue_timers * 15); reasons.append("overdue_sla")
    if inputs.critical_sla_items:
        score += 35; reasons.append("critical_sla")
    if inputs.high_sla_items:
        score += min(20, inputs.high_sla_items * 10); reasons.append("high_sla")
    if inputs.guardrail_escalations:
        score += 20; reasons.append("guardrail_escalation")
    if inputs.waiting_human_checkpoints:
        score += 15; reasons.append("human_checkpoint")
    if inputs.material_contradictions:
        score += min(20, inputs.material_contradictions * 10); reasons.append("material_contradiction")
    if inputs.claim_amount >= 10000:
        score += 10; reasons.append("high_value_claim")
    score = min(score, 100)
    band = (
        ReviewPriorityBand.CRITICAL if score >= 80 else
        ReviewPriorityBand.HIGH if score >= 55 else
        ReviewPriorityBand.NORMAL if score >= 25 else
        ReviewPriorityBand.LOW
    )
    return score, band, reasons
