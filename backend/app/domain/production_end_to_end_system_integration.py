from __future__ import annotations

RELEASE_CANDIDATE_HARDENING_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_score_release_readiness": True,
    "ai_can_summarize_cross_domain_regression": True,
    "ai_can_detect_tenant_isolation_risk": True,
    "ai_can_detect_workflow_recovery_risk": True,
    "ai_can_detect_event_stream_risk": True,
    "ai_can_detect_migration_chain_risk": True,
    "ai_can_prepare_release_candidate_report": True,
    "ai_can_declare_release_candidate": False,
    "ai_can_promote_to_production": False,
    "worker_can_declare_release_candidate": False,
    "worker_can_promote_to_production": False,
    "human_release_candidate_decision_required": True,
    "existing_production_human_approval_preserved": True,
    "tenant_isolation_is_blocking_gate": True,
    "migration_chain_is_blocking_gate": True,
    "security_readiness_is_blocking_gate": True,
    "evaluation_quality_is_blocking_gate": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
    "funds_collection_allowed": False,
    "funds_movement_allowed": False,
}

REQUIRED_CROSS_DOMAIN_STAGES = [
    "multimodal_evidence_ingestion",
    "document_intelligence",
    "healthcare_normalization_fhir",
    "multi_rag_retrieval",
    "langgraph_specialist_orchestration",
    "mcp_tool_boundary",
    "human_review",
    "governed_claim_closure",
    "regulatory_governance",
]

REQUIRED_RELEASE_GATES = [
    "cross_domain_golden_journeys",
    "api_contract_regression",
    "tenant_isolation",
    "durable_workflow_recovery",
    "event_sse_integrity",
    "failure_injection_resilience",
    "migration_chain_integrity",
    "security_readiness",
    "ai_evaluation_quality",
    "release_engineering_controls",
]


def production_end_to_end_system_integration_contract() -> dict:
    return {
        "name": "production_end_to_end_system_integration_cross_domain_regression_and_release_candidate_hardening",
        "required_cross_domain_stages": REQUIRED_CROSS_DOMAIN_STAGES,
        "required_release_gates": REQUIRED_RELEASE_GATES,
        "capabilities": [
            "deterministic_cross_domain_golden_journey_validation",
            "openapi_and_api_contract_regression",
            "cross_tenant_negative_path_verification",
            "langgraph_checkpoint_interrupt_resume_verification",
            "event_outbox_sse_ordering_and_reconnect_verification",
            "failure_injection_and_degraded_dependency_validation",
            "complete_alembic_migration_chain_validation",
            "security_and_ai_evaluation_gate_aggregation",
            "immutable_release_candidate_assessment",
            "human_only_release_candidate_declaration",
            "gitops_release_engineering_gate_reuse",
            "consolidated_production_readiness_reporting",
        ],
        "authority": RELEASE_CANDIDATE_HARDENING_AUTHORITY,
        "traceability": "multimodal ingestion -> healthcare/FHIR normalization -> Multi-RAG -> LangGraph specialists -> MCP boundary -> human review -> governed closure -> regulatory governance -> cross-domain regression -> deterministic release readiness -> human release-candidate decision -> existing human-approved production promotion",
    }
