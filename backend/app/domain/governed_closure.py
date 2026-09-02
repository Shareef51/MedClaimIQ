from __future__ import annotations

from enum import StrEnum


class DecisionPacketStatus(StrEnum):
    DRAFT = "draft"
    PENDING_SECOND_REVIEW = "pending_second_review"
    READY_TO_CLOSE = "ready_to_close"
    CLOSED = "closed"
    ESCALATED = "escalated"
    REJECTED_SECOND_REVIEW = "rejected_second_review"


class SecondReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ClosureBlockerCode(StrEnum):
    EVIDENCE_MISSING = "evidence_missing"
    EVIDENCE_NOT_READY = "evidence_not_ready"
    EVIDENCE_CHANGED = "evidence_changed"
    MATERIAL_GRAPH_CONFLICT = "material_graph_conflict"
    MATERIAL_MULTIMODAL_CONFLICT = "material_multimodal_conflict"
    REQUIRED_MODALITY_MISSING = "required_modality_missing"
    GUARDRAIL_CONFLICT = "guardrail_conflict"
    AI_DISAGREEMENT_REASON_MISSING = "ai_disagreement_reason_missing"
    PARTIAL_APPROVAL_INVALID = "partial_approval_invalid"
    REASON_CODE_MISSING = "reason_code_missing"
    RATIONALE_MISSING = "rationale_missing"


FINAL_FINANCIAL_DECISIONS = frozenset({"approve", "deny", "partial_approve"})


def ai_expected_human_decision(recommendation: str | None) -> str | None:
    return {
        "support_approval": "approve",
        "support_denial": "deny",
        "pending_documents": "request_information",
    }.get(recommendation or "")


def governed_closure_contract() -> dict[str, object]:
    return {
        "workflow": [
            "decision_packet", "evidence_completeness_validation", "unresolved_conflict_blocking",
            "decision_version_lock", "dual_control_if_required", "governed_human_closure",
            "checkpoint_resolution", "post_decision_notification_intents",
        ],
        "human_authority": {
            "authenticated_human_reviewer_required": True,
            "distinct_second_reviewer_for_dual_control": True,
            "llm_final_decision": False,
            "langgraph_final_decision": False,
            "rag_final_decision": False,
            "mcp_final_decision": False,
            "automated_financial_adjudication": False,
        },
        "concurrency": {
            "exclusive_primary_reviewer_lease": True,
            "optimistic_claim_version": True,
            "optimistic_packet_version": True,
            "locked_payload_sha256": True,
        },
        "traceability": "evidence -> agent finding -> reviewer annotation -> locked decision packet -> persisted human decision",
    }
