from __future__ import annotations

FINANCIAL_INTELLIGENCE_AUTHORITY = {
    "read_only_source_systems": True,
    "llm_can_modify_ledger": False,
    "langgraph_can_modify_ledger": False,
    "rag_can_modify_ledger": False,
    "mcp_can_modify_ledger": False,
    "analytics_worker_can_modify_ledger": False,
    "ai_can_modify_reserve": False,
    "ai_can_authorize_payment": False,
    "ai_can_close_accounting_period": False,
    "automatic_fund_movement": False,
    "recommendation_only": True,
    "ledger_citations_required": True,
}


def financial_intelligence_contract() -> dict[str, object]:
    return {
        "name": "production_financial_analytics_reserve_payment_integrity_control_intelligence",
        "workflow": [
            "governed_financial_read_model",
            "claim_reserve_tracking",
            "paid_vs_incurred",
            "financial_leakage_detection",
            "duplicate_overpayment_analytics",
            "reconciliation_anomaly_scoring",
            "provider_payment_patterns",
            "recoupment_aging",
            "reserve_variance",
            "accounting_control_exceptions",
            "period_close_readiness",
            "portfolio_kpis",
            "ledger_cited_financial_rag",
            "recommendation_only_anomaly_investigation",
            "evaluation_and_opentelemetry",
        ],
        "authority": FINANCIAL_INTELLIGENCE_AUTHORITY,
        "policy": {
            "source_of_truth_is_release40_41_governed_finance": True,
            "derived_snapshots_are_immutable": True,
            "no_source_record_mutation": True,
            "deterministic_scores_are_explainable": True,
            "copilot_requires_source_citations": True,
        },
    }
