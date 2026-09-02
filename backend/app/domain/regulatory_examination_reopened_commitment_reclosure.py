from __future__ import annotations

REOPENED_COMMITMENT_RECLOSURE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_compare_root_causes": True,
    "ai_can_recommend_control_redesign": True,
    "ai_can_score_reclosure_readiness": True,
    "ai_can_recertify_commitment": False,
    "ai_can_reclose_commitment": False,
    "worker_can_recertify_commitment": False,
    "worker_can_reclose_commitment": False,
    "human_recertification_required": True,
    "independent_revalidation_required": True,
    "second_recurrence_requires_escalation": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

RECLOSURE_STATES = ("remediating", "retesting", "revalidating", "ready_for_recertification", "reclosed", "escalated")


def reopened_commitment_reclosure_contract() -> dict:
    return {
        "name": "production_regulatory_examination_reopened_commitment_remediation_supervisory_revalidation_and_reclosure_assurance",
        "capabilities": [
            "reopened_commitment_remediation_plans",
            "renewed_milestones",
            "cross_entity_corrective_action_propagation",
            "regulator_follow_up_linkage",
            "recurrence_root_cause_comparison",
            "enhanced_control_redesign_recommendations",
            "independent_retesting",
            "second_recurrence_escalation",
            "sustainability_reset_windows",
            "human_recertification",
            "immutable_reclosure_versions",
            "sse_supervisory_events",
            "audit_export",
        ],
        "authority": REOPENED_COMMITMENT_RECLOSURE_AUTHORITY,
        "traceability": "reopened commitment -> renewed remediation -> evidence -> independent retest -> human recertification -> sustainability reset -> reclosure",
    }
