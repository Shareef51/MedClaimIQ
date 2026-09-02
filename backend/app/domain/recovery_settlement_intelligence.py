from __future__ import annotations

RECOVERY_SETTLEMENT_INTELLIGENCE_AUTHORITY = {
    "source_read_only": True,
    "derived_records_only": True,
    "ai_can_alter_balances": False,
    "llm_can_post_or_modify_journals": False,
    "langgraph_can_post_or_modify_journals": False,
    "rag_can_post_or_modify_journals": False,
    "mcp_can_post_or_modify_journals": False,
    "worker_can_verify_settlement_evidence": False,
    "worker_can_modify_closeout_certificate": False,
    "worker_can_create_bank_transaction": False,
    "worker_can_collect_funds": False,
    "automatic_fund_movement": False,
    "copilot_recommendation_only": True,
    "settlement_and_ledger_citations_required": True,
}

def recovery_settlement_intelligence_contract() -> dict[str, object]:
    return {
        "name": "production_recovery_settlement_reconciliation_intelligence_reporting",
        "workflow": [
            "governed_release47_read_model",
            "immutable_provider_balance_statement",
            "settlement_aging_intelligence",
            "repayment_offset_reconciliation_analytics",
            "under_over_recovery_detection",
            "provider_recovery_history",
            "settlement_exception_investigation",
            "accounting_period_closeout_reporting",
            "recovery_effectiveness_kpis",
            "regulatory_audit_closeout_package",
            "human_released_provider_portal_statement",
            "settlement_ledger_cited_financial_rag",
            "opentelemetry_and_sse",
        ],
        "authority": RECOVERY_SETTLEMENT_INTELLIGENCE_AUTHORITY,
        "policy": {
            "release47_source_records_are_never_mutated": True,
            "derived_snapshots_and_statements_are_immutable": True,
            "provider_statement_delivery_does_not_change_balance": True,
            "copilot_requires_governed_citations": True,
            "audit_packages_are_hash_bound": True,
        },
    }
