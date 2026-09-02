from __future__ import annotations

REGULATORY_CONTROL_TESTING_AUTHORITY = {
    "orchestration_only": True,
    "ai_can_select_risk_weighted_samples": True,
    "ai_can_summarize_test_evidence": True,
    "ai_can_propose_exceptions": True,
    "ai_can_conclude_control_effectiveness": False,
    "ai_can_certify_controls": False,
    "ai_can_approve_remediation": False,
    "ai_can_accept_residual_risk": False,
    "ai_can_close_findings": False,
    "worker_can_execute_financial_transactions": False,
    "worker_can_modify_accounting_records": False,
    "human_independent_conclusion_required": True,
}

def regulatory_control_testing_contract() -> dict:
    return {
        "name": "production_regulatory_remediation_continuous_control_testing",
        "scope": [
            "continuous_control_testing_schedules","risk_based_evidence_sampling",
            "test_population_provenance","sample_provenance","design_effectiveness_testing",
            "operating_effectiveness_testing","cross_entity_sampling","exception_detection",
            "failed_sample_aggregation","independent_tester_assignment","retest_scheduling",
            "evidence_chain_validation","human_test_conclusions","immutable_test_versions",
            "sse_testing_events","testing_evaluation",
        ],
        "authority": REGULATORY_CONTROL_TESTING_AUTHORITY,
        "traceability": "control -> population -> sample -> evidence -> test -> exception -> retest -> independent human conclusion",
        "source_of_truth": "governed control inventory, Release 56 assurance signals, immutable evidence and human conclusions",
    }
