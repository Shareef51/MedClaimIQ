from __future__ import annotations

POST_INTERVENTION_SURVEILLANCE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_detect_systemic_recurrence": True,
    "ai_can_correlate_new_examinations": True,
    "ai_can_recommend_reopening": True,
    "ai_can_reopen_intervention_program": False,
    "ai_can_close_intervention_program": False,
    "ai_can_accept_residual_systemic_risk": False,
    "ai_can_certify_effectiveness": False,
    "worker_can_reopen_intervention_program": False,
    "worker_can_certify_effectiveness": False,
    "human_reopening_approval_required": True,
    "independent_reassessment_required": True,
    "executive_and_internal_audit_escalation_required_for_systemic_recurrence": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}


def post_intervention_surveillance_contract() -> dict:
    return {
        "name": "production_regulatory_examination_post_intervention_surveillance_systemic_risk_recurrence_and_enterprise_program_reopening_governance",
        "capabilities": [
            "closed_program_surveillance", "systemic_risk_rebound_detection", "control_effectiveness_decay_monitoring",
            "new_examination_to_closed_program_matching", "cross_entity_recurrence_propagation",
            "prior_closure_and_risk_acceptance_comparison", "recurrence_investigation_cases",
            "regulator_followup_correlation", "renewed_enterprise_remediation_program_candidates",
            "independent_reassessment", "executive_internal_audit_escalation", "human_program_reopening",
            "immutable_reopening_versions", "sse_supervisory_dashboards", "audit_export",
        ],
        "authority": POST_INTERVENTION_SURVEILLANCE_AUTHORITY,
        "traceability": "closed intervention -> surveillance signal -> systemic recurrence -> human investigation -> program reopening -> renewed remediation",
    }
