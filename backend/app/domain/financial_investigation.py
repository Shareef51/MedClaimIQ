from __future__ import annotations

FINANCIAL_INVESTIGATION_AUTHORITY = {
    "anomaly_case_creation_may_be_automated": True,
    "ai_can_classify_root_cause": False,
    "ai_can_close_case": False,
    "ai_can_place_payment_hold": False,
    "ai_can_create_void_reissue": False,
    "ai_can_create_accounting_adjustment": False,
    "ai_can_approve_remediation": False,
    "llm_can_change_adjudication": False,
    "langgraph_can_change_adjudication": False,
    "rag_can_change_accounting": False,
    "mcp_can_authorize_payment": False,
    "background_worker_can_move_funds": False,
    "human_investigator_required": True,
    "material_remediation_dual_approval_required": True,
    "recommendation_only": True,
}

ROOT_CAUSE_CODES = (
    "duplicate_payment",
    "overpayment",
    "provider_billing_pattern",
    "reconciliation_mismatch",
    "returned_payment",
    "reserve_inadequacy",
    "accounting_control_gap",
    "data_quality",
    "no_issue_found",
    "other",
)

REMEDIATION_TYPES = (
    "payment_hold",
    "void_reissue_referral",
    "adjustment_referral",
    "recoupment_referral",
    "reserve_review_referral",
    "no_financial_action",
)


def financial_investigation_contract() -> dict[str, object]:
    return {
        "name": "production_financial_investigation_payment_integrity_governed_remediation",
        "workflow": [
            "release42_anomaly_to_case",
            "duplicate_overpayment_case_clustering",
            "immutable_investigation_evidence_pack",
            "human_finance_investigator_assignment_and_lease",
            "evidence_and_citation_review",
            "human_root_cause_classification",
            "recommendation_only_ai_support",
            "human_annotations",
            "governed_remediation_proposal",
            "material_remediation_second_approval",
            "release40_41_referral_execution_by_humans",
            "sla_and_sse",
            "immutable_audit_chain",
            "human_case_closure",
        ],
        "root_cause_codes": ROOT_CAUSE_CODES,
        "remediation_types": REMEDIATION_TYPES,
        "authority": FINANCIAL_INVESTIGATION_AUTHORITY,
    }
