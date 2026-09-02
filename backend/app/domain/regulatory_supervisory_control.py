from __future__ import annotations

REGULATORY_SUPERVISORY_AUTHORITY = {
    "ai_can_certify_reconciliation": False,
    "langgraph_can_certify_reconciliation": False,
    "rag_can_certify_reconciliation": False,
    "mcp_can_certify_reconciliation": False,
    "worker_can_certify_reconciliation": False,
    "worker_can_authorize_submission": False,
    "worker_can_change_financial_or_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_funds": False,
    "worker_can_move_money": False,
    "independent_human_supervisory_signoff_required": True,
    "monitoring_and_recommendation_only_automation": True,
}


def regulatory_supervisory_control_contract() -> dict[str, object]:
    return {
        "name": "production_regulatory_submission_supervisory_control_reconciliation_certification",
        "workflow": [
            "release49_certified_package",
            "release50_human_release_and_transport",
            "cryptographically_verified_acknowledgment",
            "supervisory_reconciliation_case",
            "submission_aging_and_sla_investigation",
            "certified_package_to_regulator_tieout",
            "rejection_root_cause_and_amendment_effectiveness",
            "deterministic_delivery_control_attestation",
            "evidence_sampling_and_compliance_exception_gate",
            "independent_human_supervisory_signoff",
            "immutable_reconciliation_certification",
            "audit_export_and_regulator_correspondence",
        ],
        "authority": REGULATORY_SUPERVISORY_AUTHORITY,
        "policy": {
            "certification_is_human_only": True,
            "maker_checker_separation_required": True,
            "material_exceptions_block_certification": True,
            "acknowledgments_must_be_cryptographically_verified": True,
            "financial_and_accounting_sources_are_read_only": True,
            "supervision_never_authorizes_submission_or_fund_movement": True,
        },
    }
