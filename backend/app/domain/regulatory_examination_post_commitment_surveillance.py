from __future__ import annotations

POST_COMMITMENT_SURVEILLANCE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_detect_recurrence": True,
    "ai_can_score_sustainability_decay": True,
    "ai_can_compare_prior_certification": True,
    "ai_can_reopen_commitment": False,
    "ai_can_close_regulatory_commitment": False,
    "worker_can_reopen_commitment": False,
    "worker_can_certify_effectiveness": False,
    "human_reopen_decision_required": True,
    "independent_reassessment_required_after_reopen": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

SURVEILLANCE_STATES = ("stable", "watch", "degrading", "recurrence_candidate", "reopened")
INVESTIGATION_STATES = ("open", "triage", "under_review", "reopen_recommended", "dismissed", "reopened")


def post_commitment_surveillance_contract() -> dict:
    return {
        "name": "production_regulatory_examination_post_commitment_surveillance_recurrence_investigation_and_supervisory_reopening_assurance",
        "capabilities": [
            "closed_commitment_surveillance",
            "sustainability_decay_detection",
            "recurring_commitment_control_failure_correlation",
            "new_examination_to_closed_commitment_matching",
            "cross_entity_recurrence_propagation",
            "prior_certification_comparison",
            "recurrence_investigation_cases",
            "renewed_action_plan_linkage",
            "regulator_follow_up_escalation",
            "independent_reassessment",
            "human_reopening_approval",
            "immutable_reopening_versions",
            "sse_supervisory_events",
            "audit_export",
        ],
        "authority": POST_COMMITMENT_SURVEILLANCE_AUTHORITY,
        "traceability": "closed commitment -> surveillance signal -> recurrence evidence -> human reopening -> renewed corrective action -> revalidation",
    }
