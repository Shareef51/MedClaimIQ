from __future__ import annotations

REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_propose_renewed_remediation": True,
    "ai_can_compare_root_causes": True,
    "ai_can_recommend_control_redesign": True,
    "ai_can_approve_remediation_program": False,
    "ai_can_accept_residual_systemic_risk": False,
    "ai_can_certify_effectiveness": False,
    "ai_can_reclose_intervention_program": False,
    "worker_can_approve_or_reclose": False,
    "independent_revalidation_required": True,
    "human_residual_risk_reassessment_required": True,
    "executive_recertification_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}


def reopened_enterprise_intervention_contract() -> dict:
    return {
        "name": "production_regulatory_examination_reopened_enterprise_intervention_execution_renewed_systemic_remediation_and_independent_revalidation_governance",
        "capabilities": [
            "reopened_intervention_plan", "renewed_systemic_corrective_actions",
            "prior_vs_current_root_cause_comparison", "cross_entity_remediation_propagation",
            "enhanced_control_redesign_tracking", "renewed_regulator_commitment_linkage",
            "evidence_bound_milestones", "second_systemic_recurrence_escalation",
            "independent_effectiveness_revalidation", "sustainability_reset",
            "human_residual_systemic_risk_reassessment", "executive_recertification",
            "immutable_reclosure_versions", "sse_supervisory_dashboard", "audit_export",
        ],
        "authority": REOPENED_ENTERPRISE_INTERVENTION_AUTHORITY,
        "traceability": "reopened intervention -> renewed remediation -> evidence -> independent revalidation -> human risk reassessment -> executive reclosure",
    }
