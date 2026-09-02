from __future__ import annotations

from enum import StrEnum


class DecisionNoticeStatus(StrEnum):
    DRAFT = "draft"
    RELEASED = "released"
    DELIVERY_PENDING = "delivery_pending"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    DEAD_LETTERED = "dead_lettered"


class AppealStatus(StrEnum):
    SUBMITTED = "submitted"
    LATE_PENDING_REVIEW = "late_pending_review"
    TRIAGE = "triage"
    IN_REVIEW = "in_review"
    WAITING_SUPPLEMENTAL_EVIDENCE = "waiting_supplemental_evidence"
    RESOLVED = "resolved"
    REJECTED_UNTIMELY = "rejected_untimely"
    WITHDRAWN = "withdrawn"


class AppealResolutionOutcome(StrEnum):
    AFFIRM = "affirm"
    MODIFY = "modify"
    OVERTURN = "overturn"
    REQUEST_INFORMATION = "request_information"


class PostDecisionTaskType(StrEnum):
    NOTICE_RELEASE = "notice_release"
    NOTICE_DELIVERY = "notice_delivery"
    APPEAL_TRIAGE = "appeal_triage"
    APPEAL_REVIEW = "appeal_review"
    SUPPLEMENTAL_EVIDENCE_REVIEW = "supplemental_evidence_review"


REASON_CODE_EXPLANATIONS: dict[str, str] = {
    "evidence_supports": "The submitted and verified evidence supports the reviewed outcome.",
    "evidence_contradicts": "Verified evidence contains material information that conflicts with the requested outcome.",
    "policy_coverage": "The reviewed benefit or coverage terms affected the outcome.",
    "coding_issue": "The submitted service or billing coding required an adjustment based on reviewed evidence.",
    "duplicate_risk": "The reviewed record contains evidence of a duplicate or overlapping claim item.",
    "fraud_waste_signal": "A material fraud, waste, or abuse concern required additional human review.",
    "missing_documents": "Required supporting documentation was not available in the locked evidence set.",
    "human_judgment": "An authorized reviewer applied documented human judgment to the evidence.",
    "other": "The authorized reviewer documented another evidence-backed reason for the outcome.",
}


def post_decision_contract() -> dict[str, object]:
    return {
        "workflow": [
            "locked_human_decision",
            "decision_notice_draft",
            "human_notice_release",
            "delivery_orchestration",
            "appeal_intake",
            "supplemental_evidence",
            "independent_appeal_assignment",
            "controlled_reopening",
            "human_reconsideration_resolution",
            "immutable_decision_history",
        ],
        "traceability": "original evidence -> original locked human decision -> released notice -> appeal -> supplemental evidence -> independent human reconsideration -> controlling resolution",
        "human_authority": {
            "ai_may_draft_or_summarize": True,
            "ai_may_organize_evidence": True,
            "llm_may_issue_or_overturn": False,
            "langgraph_may_issue_or_overturn": False,
            "rag_may_issue_or_overturn": False,
            "mcp_may_issue_or_overturn": False,
            "automation_may_issue_or_overturn": False,
            "automation_may_deliver_human_released_communications": True,
            "authorized_human_required_for_notice_release": True,
            "independent_authorized_human_required_for_appeal_resolution": True,
            "automated_financial_execution": False,
        },
    }
