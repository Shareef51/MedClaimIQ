from __future__ import annotations

RECLOSED_RECOVERY_SUSTAINABILITY_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_score_recovery_decay": True,
    "ai_can_detect_multi_cycle_recurrence": True,
    "ai_can_score_enterprise_materiality": True,
    "ai_can_correlate_regulator_followups": True,
    "ai_can_open_authoritative_investigation": False,
    "ai_can_reopen_or_reclose_program": False,
    "ai_can_accept_residual_systemic_risk": False,
    "ai_can_certify_recovery_effectiveness": False,
    "worker_can_open_authoritative_investigation": False,
    "worker_can_reopen_program": False,
    "mandatory_human_investigation_for_repeated_failure": True,
    "mandatory_executive_internal_audit_challenge": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

def reclosed_recovery_sustainability_contract() -> dict:
    return {
        "name": "production_regulatory_examination_reclosed_recovery_sustainability_monitoring_multi_cycle_recovery_recurrence_intelligence_and_enterprise_supervisory_escalation",
        "capabilities": [
            "post_reclosure_sustainability_surveillance",
            "multi_cycle_recovery_decay_scoring",
            "repeated_recovery_failure_detection",
            "systemic_risk_rebound_correlation",
            "cross_entity_recurrence_propagation",
            "prior_recertification_reclosure_comparison",
            "regulator_followup_correlation",
            "enterprise_materiality_escalation",
            "renewed_supervisory_investigation_cases",
            "mandatory_executive_internal_audit_challenge",
            "immutable_escalation_versions",
            "sse_supervisory_updates",
            "audit_exports",
        ],
        "authority": RECLOSED_RECOVERY_SUSTAINABILITY_AUTHORITY,
        "traceability": "reclosed recovery -> sustainability surveillance -> multi-cycle recurrence -> enterprise escalation -> human investigation",
    }
