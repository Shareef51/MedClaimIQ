from __future__ import annotations

REGULATORY_DEFICIENCY_LIFECYCLE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_prioritize_investigations": True,
    "ai_can_propose_root_cause_links": True,
    "ai_can_propose_material_weakness_candidate": True,
    "ai_can_draft_corrective_action": True,
    "ai_can_formally_classify_material_weakness": False,
    "ai_can_approve_corrective_action": False,
    "ai_can_accept_residual_risk": False,
    "ai_can_certify_control_effectiveness": False,
    "ai_can_close_enterprise_issue": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_move_money": False,
    "independent_human_challenge_required": True,
    "executive_human_attestation_required": True,
}

def regulatory_deficiency_lifecycle_contract() -> dict:
    return {
        "name": "production_regulatory_remediation_enterprise_deficiency_lifecycle",
        "scope": [
            "deficiency_investigation_cases", "formal_severity_review", "material_weakness_candidate_governance",
            "cross_control_impact_analysis", "root_cause_linkage", "executive_corrective_action_plans",
            "accountable_owners", "remediation_milestones", "regulatory_commitment_linkage",
            "compensating_control_expiry_monitoring", "recurring_deficiency_detection", "overdue_action_escalation",
            "independent_challenge", "executive_attestation", "immutable_disposition_history", "sse_dashboard_events",
            "audit_export", "deficiency_lifecycle_evaluation",
        ],
        "authority": REGULATORY_DEFICIENCY_LIFECYCLE_AUTHORITY,
        "traceability": "exception -> deficiency -> enterprise issue -> human classification -> corrective action -> retest -> independent validation -> executive closure",
        "source_of_truth": "immutable Release 58 assurance deficiencies plus governed Release 59 human decisions and corrective-action evidence",
    }
