from __future__ import annotations

REGULATORY_TRANSPORT_AUTHORITY = {
    "ai_can_certify_report": False,
    "ai_can_authorize_submission_release": False,
    "langgraph_can_authorize_submission_release": False,
    "rag_can_authorize_submission_release": False,
    "mcp_can_authorize_submission_release": False,
    "worker_can_authorize_submission_release": False,
    "worker_can_change_financial_or_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_funds": False,
    "worker_can_move_money": False,
    "human_release_required": True,
    "automatic_submission_authorization": False,
}


def regulatory_submission_transport_contract() -> dict[str, object]:
    return {
        "name": "production_regulatory_submission_transport_acknowledgment_reconciliation",
        "workflow": [
            "certified_release49_package",
            "one_time_human_submission_release",
            "destination_registry_and_schema_validation",
            "encrypted_signed_submission_envelope",
            "lease_bound_idempotent_transport",
            "retry_backoff_circuit_breaker_dlq",
            "cryptographic_acknowledgment_verification",
            "acceptance_or_rejection_reconciliation",
            "correction_amendment_resubmission_lineage",
            "immutable_transmission_provenance",
            "submission_sla_and_supervisory_operations",
        ],
        "authority": REGULATORY_TRANSPORT_AUTHORITY,
        "policy": {
            "release_is_one_time_and_package_version_bound": True,
            "only_certified_locked_packages_are_releasable": True,
            "transport_workers_may_execute_but_never_authorize": True,
            "acknowledgments_require_signature_verification": True,
            "rejected_submissions_require_human_governed_correction_or_amendment": True,
            "financial_and_accounting_sources_are_read_only": True,
        },
    }
