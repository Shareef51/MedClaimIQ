from __future__ import annotations

REGULATORY_ASSURANCE_DEFICIENCY_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_classify_sample_exceptions": True,
    "ai_can_propose_deficiency_clusters": True,
    "ai_can_score_candidate_severity": True,
    "ai_can_propose_enterprise_issue_escalation": True,
    "ai_can_declare_material_weakness": False,
    "ai_can_certify_control_effectiveness": False,
    "ai_can_approve_remediation": False,
    "ai_can_accept_residual_risk": False,
    "ai_can_close_findings_or_deficiencies": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_move_money": False,
    "human_independent_escalation_required": True,
    "human_closure_required": True,
}

def regulatory_assurance_deficiency_contract() -> dict:
    return {
        "name": "production_regulatory_remediation_assurance_exceptions_deficiency_aggregation",
        "scope": [
            "sample_exception_classification", "deficiency_severity_scoring",
            "repeated_exception_correlation", "control_deficiency_aggregation",
            "cross_entity_issue_propagation", "design_vs_operating_deficiency",
            "compensating_control_assessment", "remediation_linkage", "issue_aging_sla",
            "material_weakness_candidate_detection", "independent_human_escalation",
            "immutable_deficiency_versions", "sse_enterprise_issue_alerts", "deficiency_evaluation",
        ],
        "authority": REGULATORY_ASSURANCE_DEFICIENCY_AUTHORITY,
        "traceability": "sample failure -> exception -> deficiency -> enterprise issue -> remediation -> retest -> independent human closure",
        "source_of_truth": "Release 57 immutable sample/test evidence plus governed remediation and human assurance decisions",
    }
