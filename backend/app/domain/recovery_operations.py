from __future__ import annotations

RECOVERY_AUTHORITY = {
    "ai_can_analyze_recovery": True,
    "ai_can_recommend_dispute_outcome": True,
    "ai_can_adjudicate_provider_dispute": False,
    "ai_can_approve_accounting_change": False,
    "ai_can_authorize_payment": False,
    "ai_can_collect_funds": False,
    "llm_can_move_money": False,
    "langgraph_can_move_money": False,
    "rag_can_move_money": False,
    "mcp_can_move_money": False,
    "background_worker_can_move_money": False,
    "independent_human_dispute_resolution_required": True,
    "material_dispute_dual_control_required": True,
    "recommendation_only": True,
}

RECOVERY_TYPES = (
    "recoupment_recovery",
    "adjustment_recovery",
    "payment_hold_verification",
    "void_reissue_verification",
    "reserve_review_verification",
)
DISPUTE_OUTCOMES = ("uphold_recovery", "reduce_recovery", "withdraw_recovery", "request_information")
CLOSURE_REASONS = ("fully_recovered", "partially_recovered", "remediation_verified", "recovery_exhausted", "no_recovery_due", "provider_dispute_resolved")


def recovery_operations_contract() -> dict[str, object]:
    return {
        "name": "production_recovery_provider_dispute_and_outcome_verification",
        "workflow": [
            "release43_governed_referral_to_recovery_case",
            "immutable_recovery_evidence_pack",
            "human_recovery_investigator_lease",
            "downstream_remediation_outcome_monitoring",
            "partial_multi_recovery_reconciliation",
            "provider_dispute_intake_and_evidence",
            "material_dispute_escalation",
            "independent_human_dispute_resolution",
            "recovery_correspondence_provenance",
            "remediation_effectiveness_verification",
            "aging_sla_and_sse",
            "immutable_recovery_audit_chain",
            "human_recovery_case_closure",
        ],
        "recovery_types": RECOVERY_TYPES,
        "dispute_outcomes": DISPUTE_OUTCOMES,
        "closure_reasons": CLOSURE_REASONS,
        "authority": RECOVERY_AUTHORITY,
    }
