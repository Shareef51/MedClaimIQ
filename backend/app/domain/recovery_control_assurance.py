from __future__ import annotations

RECOVERY_CONTROL_ASSURANCE_AUTHORITY = {
    "source_financial_records_read_only": True,
    "ai_can_prepare_or_summarize": True,
    "ai_can_flag_control_issues": True,
    "ai_can_certify_regulatory_report": False,
    "langgraph_can_certify_regulatory_report": False,
    "rag_can_certify_regulatory_report": False,
    "mcp_can_certify_regulatory_report": False,
    "worker_can_certify_or_stage_submission": False,
    "worker_can_record_external_submission_receipt": False,
    "worker_can_modify_balances_or_journals": False,
    "worker_can_authorize_payments": False,
    "worker_can_create_bank_transaction": False,
    "worker_can_collect_funds": False,
    "automatic_regulatory_submission": False,
    "automatic_fund_movement": False,
    "maker_checker_certification_required": True,
}


def recovery_control_assurance_contract() -> dict[str, object]:
    return {
        "name": "production_recovery_portfolio_control_assurance_regulatory_submission_governance",
        "workflow": [
            "regulatory_reporting_period",
            "deterministic_portfolio_control_attestation",
            "reconciliation_to_ledger_tie_out",
            "provider_statement_completeness",
            "control_evidence_sampling",
            "submission_package_versioning_and_lock",
            "independent_maker_checker_certification",
            "human_regulatory_submission_staging",
            "external_submission_receipt_recording",
            "correction_and_amendment_versioning",
            "audit_annotations_and_immutable_certification_chain",
            "retention_and_legal_hold_manifest",
            "control_effectiveness_kpis_and_sse",
        ],
        "authority": RECOVERY_CONTROL_ASSURANCE_AUTHORITY,
        "policy": {
            "material_control_exceptions_block_lock_and_certification": True,
            "package_manifest_is_hash_locked_before_certification": True,
            "maker_and_checker_must_be_different_humans": True,
            "external_submission_is_never_automatic": True,
            "submission_receipt_requires_authorized_human_actor": True,
            "source_financial_and_accounting_records_are_never_mutated": True,
            "legal_hold_and_retention_are_captured_in_the_package_manifest": True,
        },
    }
