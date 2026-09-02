from __future__ import annotations

EXAMINATION_READINESS_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_classify_requests": True,
    "ai_can_retrieve_and_map_evidence": True,
    "ai_can_detect_duplicate_or_conflicting_evidence": True,
    "ai_can_draft_cited_responses": True,
    "ai_can_simulate_examiner_questions": True,
    "ai_can_approve_regulator_response": False,
    "ai_can_transmit_to_regulator": False,
    "ai_can_certify_controls": False,
    "ai_can_close_findings": False,
    "ai_can_accept_residual_risk": False,
    "worker_can_approve_submission_package": False,
    "worker_can_transmit_submission": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_or_move_money": False,
    "human_approval_required_for_response": True,
    "human_approval_required_for_submission_package": True,
}

REQUEST_STATUSES = ("received", "triaged", "evidence_mapping", "drafting", "human_review", "approved", "submitted", "closed")
EVIDENCE_CLASSES = ("standard", "confidential", "restricted", "regulatory_privileged", "legal_privileged")
ROOM_STATUSES = ("assembling", "review_ready", "human_approved", "locked")


def examination_readiness_contract() -> dict:
    return {
        "name": "production_regulatory_examination_readiness_operations_supervisory_evidence_rooms_and_governed_regulator_interaction_preparation",
        "capabilities": [
            "examination_scope_intake",
            "regulator_request_tracking",
            "request_to_evidence_mapping",
            "governed_evidence_rooms",
            "privileged_document_segregation",
            "duplicate_and_conflict_detection",
            "completeness_and_readiness_scoring",
            "cited_response_drafting",
            "responsible_owner_assignment",
            "sla_and_deadline_monitoring",
            "examiner_question_simulation",
            "historical_examination_comparison",
            "human_response_approval",
            "immutable_submission_packages",
            "sse_readiness_events",
        ],
        "request_statuses": REQUEST_STATUSES,
        "evidence_classes": EVIDENCE_CLASSES,
        "room_statuses": ROOM_STATUSES,
        "authority": EXAMINATION_READINESS_AUTHORITY,
        "traceability": "regulator request -> authoritative knowledge -> evidence -> cited draft -> human validation -> approved examination package",
    }
