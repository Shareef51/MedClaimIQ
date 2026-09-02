from __future__ import annotations

REOPENED_OUTCOME_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_compare_prior_and_current_root_causes": True,
    "ai_can_score_recurrence_containment": True,
    "ai_can_monitor_renewed_commitments": True,
    "ai_can_recommend_reclosure_readiness": True,
    "ai_can_reclose_finding": False,
    "ai_can_recertify_control_effectiveness": False,
    "ai_can_accept_residual_risk": False,
    "worker_can_reclose_finding": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_or_move_money": False,
    "independent_revalidation_required": True,
    "human_recertification_required": True,
    "human_reclosure_approval_required": True,
}


def reopened_outcome_validation_contract() -> dict:
    return {
        "name": "production_regulatory_reopened_issue_outcome_validation_and_reclosure_assurance",
        "scope": [
            "renewed_remediation_plan_validation",
            "reopened_issue_milestones",
            "prior_vs_current_root_cause_comparison",
            "before_after_control_effectiveness",
            "recurrence_containment_testing",
            "cross_entity_remediation_propagation",
            "renewed_regulator_commitments",
            "independent_revalidation_evidence",
            "sustainability_reset_periods",
            "second_recurrence_escalation",
            "human_recertification",
            "immutable_reclosure_versions",
            "sse_supervisory_events",
            "audit_exports",
        ],
        "authority": REOPENED_OUTCOME_AUTHORITY,
        "traceability": "reopened finding -> renewed remediation -> corrective action -> retest -> independent revalidation -> sustainability monitoring -> human recertification -> reclosure",
    }
