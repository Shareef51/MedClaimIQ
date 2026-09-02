from __future__ import annotations

COMMITMENT_EFFECTIVENESS_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_score_readiness": True,
    "ai_can_detect_recurrence": True,
    "ai_can_monitor_sustainability": True,
    "ai_can_certify_commitment_completion": False,
    "ai_can_close_regulatory_obligation": False,
    "ai_can_reopen_commitment": False,
    "worker_can_certify_closure": False,
    "human_closure_certification_required": True,
    "human_reopen_decision_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

EFFECTIVENESS_RESULTS = ("effective", "partially_effective", "ineffective")
CLOSURE_STATUSES = ("validation_pending", "closure_review", "certified_closed", "sustainability_monitoring", "reopen_candidate", "reopened")
SUSTAINABILITY_STATES = ("not_started", "monitoring", "stable", "degrading", "failed")


def commitment_effectiveness_contract() -> dict:
    return {
        "name": "production_regulatory_examination_commitment_effectiveness_validation_supervisory_closure_readiness_and_post_commitment_sustainability_assurance",
        "capabilities": [
            "commitment_completion_readiness_scoring",
            "milestone_completion_reconciliation",
            "evidence_sufficiency_validation",
            "independent_effectiveness_retesting",
            "cross_entity_implementation_verification",
            "unresolved_dependency_blockers",
            "regulator_follow_up_completion_reconciliation",
            "human_closure_certification",
            "sustainability_monitoring_windows",
            "commitment_recurrence_detection",
            "reopen_candidate_governance",
            "immutable_closure_versions",
            "sse_assurance_events",
            "audit_export",
        ],
        "authority": COMMITMENT_EFFECTIVENESS_AUTHORITY,
        "traceability": "commitment -> milestone -> evidence -> effectiveness validation -> human certification -> sustainability surveillance",
    }
