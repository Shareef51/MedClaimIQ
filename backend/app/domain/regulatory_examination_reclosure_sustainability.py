from __future__ import annotations

RECLOSURE_SUSTAINABILITY_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_score_sustainability_decay": True,
    "ai_can_detect_repeat_recurrence": True,
    "ai_can_detect_systemic_patterns": True,
    "ai_can_reopen_commitment": False,
    "ai_can_close_escalation": False,
    "worker_can_reopen_commitment": False,
    "worker_can_certify_effectiveness": False,
    "mandatory_human_investigation": True,
    "third_occurrence_requires_executive_and_internal_audit_review": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

def reclosure_sustainability_contract() -> dict:
    return {
        "name": "production_regulatory_examination_reclosure_sustainability_monitoring_repeat_recurrence_governance_and_supervisory_escalation_assurance",
        "capabilities": [
            "post_reclosure_sustainability_surveillance","repeat_recurrence_scoring","third_occurrence_systemic_pattern_detection",
            "renewed_control_health_monitoring","regulator_follow_up_surveillance","cross_entity_recurrence_propagation",
            "prior_reclosure_comparison","supervisory_escalation_tiers","mandatory_executive_internal_audit_review",
            "immutable_escalation_versions","sse_supervisory_events","audit_export"
        ],
        "authority": RECLOSURE_SUSTAINABILITY_AUTHORITY,
        "traceability": "reclosed commitment -> sustainability signal -> repeat recurrence -> supervisory escalation -> human investigation -> renewed governance action",
    }
