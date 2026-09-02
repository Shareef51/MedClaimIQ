from __future__ import annotations

RECLOSED_RECOVERY_SURVEILLANCE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_monitor_reclosed_recovery": True,
    "ai_can_detect_systemic_recovery_decay": True,
    "ai_can_propose_reopening_candidate": True,
    "ai_can_reopen_program": False,
    "ai_can_reclose_program": False,
    "ai_can_accept_residual_systemic_risk": False,
    "ai_can_certify_recovery_effectiveness": False,
    "worker_can_reopen_program": False,
    "independent_reassessment_required": True,
    "executive_and_internal_audit_review_required": True,
    "human_reopening_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}


def reclosed_recovery_surveillance_contract() -> dict:
    return {
        "name": "production_regulatory_examination_reclosed_recovery_surveillance_systemic_recovery_decay_detection_and_enterprise_reopening_assurance",
        "capabilities": [
            "post_reclosure_recovery_surveillance",
            "systemic_risk_rebound_detection",
            "recovery_effectiveness_decay_monitoring",
            "cross_entity_regression_correlation",
            "new_examination_finding_matching",
            "prior_recovery_certification_comparison",
            "sustainability_breach_investigations",
            "regulator_follow_up_correlation",
            "renewed_enterprise_reopening_candidates",
            "independent_reassessment",
            "executive_internal_audit_escalation",
            "immutable_surveillance_reopening_versions",
            "sse_supervisory_updates",
            "audit_exports",
        ],
        "authority": RECLOSED_RECOVERY_SURVEILLANCE_AUTHORITY,
        "traceability": "reclosed recovery -> surveillance signal -> systemic decay -> human investigation -> enterprise reopening -> renewed remediation",
    }
