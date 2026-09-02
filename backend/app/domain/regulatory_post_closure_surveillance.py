from __future__ import annotations

POST_CLOSURE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_match_new_findings_to_closed_findings": True,
    "ai_can_score_recurrence_and_regression": True,
    "ai_can_monitor_regulator_followups": True,
    "ai_can_create_reopen_candidate": True,
    "ai_can_reopen_finding": False,
    "ai_can_close_reopened_finding": False,
    "ai_can_accept_residual_risk": False,
    "ai_can_certify_control_effectiveness": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_or_move_money": False,
    "human_reopening_approval_required": True,
    "independent_revalidation_required_after_reopen": True,
}

def post_closure_surveillance_contract() -> dict:
    return {
        "name": "production_regulatory_post_closure_surveillance_recurrence_and_reopening_governance",
        "scope": [
            "long_term_post_closure_surveillance", "recurring_deficiency_detection", "sustainability_decay_scoring",
            "new_examination_to_closed_finding_matching", "control_regression_detection", "reopened_issue_investigation",
            "prior_certification_comparison", "cross_entity_recurrence_propagation", "regulator_followup_tracking",
            "human_reopening_approval", "renewed_corrective_action_linkage", "sse_recurrence_events",
            "immutable_reopening_versions", "audit_exports",
        ],
        "authority": POST_CLOSURE_AUTHORITY,
        "traceability": "closed issue -> surveillance signal -> recurrence evidence -> human reopening -> renewed remediation -> revalidation",
    }
