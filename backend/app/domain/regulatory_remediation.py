from __future__ import annotations

REGULATORY_REMEDIATION_AUTHORITY = {
    "ai_can_approve_remediation": False,
    "langgraph_can_approve_remediation": False,
    "rag_can_approve_remediation": False,
    "mcp_can_approve_remediation": False,
    "worker_can_approve_remediation": False,
    "worker_can_close_finding": False,
    "worker_can_represent_human_regulatory_authority": False,
    "worker_can_alter_financial_or_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_funds": False,
    "worker_can_move_money": False,
    "human_remediation_approval_required": True,
    "independent_closure_certification_required": True,
    "ai_assistance_is_recommendation_only": True,
}

def regulatory_remediation_contract() -> dict[str, object]:
    return {
        "name": "production_regulatory_findings_remediation_corrective_action_closure_assurance",
        "workflow": [
            "regulatory_finding",
            "versioned_corrective_action_plan",
            "corrective_preventive_tasks_and_dependencies",
            "evidence_bound_implementation_checkpoint",
            "deterministic_material_risk_and_impact_analysis",
            "recommendation_only_ai_assistance",
            "independent_human_plan_approval",
            "implementation_evidence",
            "independent_control_retest",
            "remediation_effectiveness_verification",
            "regulator_follow_up_response",
            "exception_waiver_governance",
            "independent_human_closure_certification",
        ],
        "authority": REGULATORY_REMEDIATION_AUTHORITY,
        "policy": {
            "material_findings_require_release53_closure": True,
            "maker_checker_separation_required": True,
            "task_dependency_enforcement": True,
            "implementation_evidence_required": True,
            "passing_retest_required": True,
            "open_waivers_block_effective_closure": True,
            "financial_accounting_analysis_is_read_only": True,
        },
    }
