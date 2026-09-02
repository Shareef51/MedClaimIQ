from __future__ import annotations

REPEATED_RECOVERY_FAILURE_INVESTIGATION_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_reconstruct_recovery_evidence": True,
    "ai_can_reassess_recovery_root_cause": True,
    "ai_can_analyze_failed_control_rehabilitation": True,
    "ai_can_map_cross_entity_causality": True,
    "ai_can_assess_regulator_followup_impact": True,
    "ai_can_propose_renewed_recovery_strategy": True,
    "ai_can_authorize_remediation": False,
    "ai_can_accept_residual_systemic_risk": False,
    "ai_can_certify_recovery_effectiveness": False,
    "ai_can_close_regulatory_commitments": False,
    "worker_can_authorize_remediation": False,
    "worker_can_certify_recovery": False,
    "independent_internal_audit_challenge_required": True,
    "executive_human_authorization_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}

def repeated_recovery_failure_investigation_contract() -> dict:
    return {
        "name": "production_regulatory_examination_repeated_recovery_failure_investigation_enterprise_recovery_root_cause_reassessment_and_supervisory_remediation_reauthorization",
        "capabilities": [
            "formal_repeated_recovery_failure_investigations",
            "multi_cycle_recovery_evidence_reconstruction",
            "prior_recovery_assumption_validation",
            "enterprise_recovery_root_cause_reassessment",
            "failed_control_rehabilitation_analysis",
            "cross_entity_causal_mapping",
            "regulatory_follow_up_impact_analysis",
            "renewed_recovery_strategy_candidates",
            "remediation_reauthorization_packages",
            "independent_internal_audit_challenge",
            "executive_authorization_gates",
            "immutable_investigation_conclusions",
            "sse_supervisory_alerts",
            "audit_exports",
        ],
        "authority": REPEATED_RECOVERY_FAILURE_INVESTIGATION_AUTHORITY,
        "traceability": "multi-cycle recovery failure -> investigation -> root-cause reassessment -> renewed recovery strategy -> human remediation reauthorization",
    }
