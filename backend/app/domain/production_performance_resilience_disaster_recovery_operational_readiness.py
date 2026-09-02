from __future__ import annotations

OPERATIONAL_READINESS_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_generate_load_and_failure_scenarios": True,
    "ai_can_score_slo_capacity_and_dr_readiness": True,
    "ai_can_detect_operational_risk": True,
    "ai_can_prepare_go_live_evidence_pack": True,
    "ai_can_approve_operational_exception": False,
    "ai_can_accept_operational_risk": False,
    "ai_can_issue_operational_certification": False,
    "ai_can_promote_to_production": False,
    "worker_can_approve_operational_exception": False,
    "worker_can_issue_operational_certification": False,
    "release107_human_release_candidate_decision_required": True,
    "release108_human_release_security_certification_required": True,
    "tenant_isolation_failure_non_bypassable": True,
    "data_loss_or_corruption_non_bypassable": True,
    "backup_restore_failure_non_bypassable": True,
    "rpo_rto_breach_non_bypassable": True,
    "unsafe_model_fallback_non_bypassable": True,
    "sev1_operational_risk_non_bypassable": True,
    "human_operational_acceptance_required": True,
    "human_go_live_readiness_certification_required": True,
    "production_promotion_separately_human_approved": True,
    "synthetic_or_deidentified_drill_data_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
    "funds_collection_allowed": False,
    "funds_movement_allowed": False,
}

REQUIRED_LOAD_PROFILES = ["baseline", "load", "stress", "soak"]
REQUIRED_AI_SLO_COMPONENTS = ["llm", "embeddings", "rag_retrieval", "reranker", "langgraph", "mcp"]
REQUIRED_DEPENDENCY_DRILLS = ["postgresql", "redis", "kafka", "vector_store", "object_storage", "llm_provider"]
REQUIRED_KUBERNETES_DRILLS = ["pod_loss", "node_loss", "availability_zone_loss"]
REQUIRED_OBSERVABILITY_SURFACES = ["api", "workers", "rag", "agents", "mcp", "datastores", "event_stream", "kubernetes"]
REQUIRED_OPERATIONAL_GATES = [
    "load_stress_soak",
    "tenant_noisy_neighbor",
    "ai_rag_agent_slo_cost",
    "dependency_resilience",
    "provider_outage_fallback",
    "kubernetes_disruption",
    "backup_restore",
    "dr_rpo_rto",
    "failover_failback",
    "autoscaling_capacity",
    "observability_alert_runbooks",
    "incident_response_exercise",
    "release107_release_candidate",
    "release108_security_certification",
]
NON_BYPASSABLE_CATEGORIES = {
    "tenant_isolation_failure",
    "data_loss",
    "data_corruption",
    "backup_restore_failure",
    "rpo_breach",
    "rto_breach",
    "unsafe_model_fallback",
    "sev1_operational_risk",
}


def production_performance_resilience_dr_operational_readiness_contract() -> dict:
    return {
        "name": "production_performance_resilience_disaster_recovery_and_operational_go_live_readiness_certification",
        "required_load_profiles": REQUIRED_LOAD_PROFILES,
        "required_ai_slo_components": REQUIRED_AI_SLO_COMPONENTS,
        "required_dependency_drills": REQUIRED_DEPENDENCY_DRILLS,
        "required_kubernetes_drills": REQUIRED_KUBERNETES_DRILLS,
        "required_observability_surfaces": REQUIRED_OBSERVABILITY_SURFACES,
        "required_operational_gates": REQUIRED_OPERATIONAL_GATES,
        "non_bypassable_categories": sorted(NON_BYPASSABLE_CATEGORIES),
        "capabilities": [
            "production_scale_load_stress_and_soak_assessment",
            "multi_tenant_concurrency_and_noisy_neighbor_isolation",
            "ai_rag_agent_latency_throughput_token_and_cost_slo_validation",
            "postgres_redis_kafka_vector_object_store_failure_testing",
            "llm_provider_outage_timeout_rate_limit_and_safe_fallback_validation",
            "kubernetes_pod_node_and_availability_zone_disruption_exercises",
            "backup_restore_integrity_and_recoverability_verification",
            "measured_rpo_rto_and_disaster_recovery_objectives",
            "cross_region_failover_and_failback_validation",
            "autoscaling_capacity_headroom_and_saturation_forecasting",
            "observability_alerting_runbook_and_oncall_verification",
            "incident_command_escalation_and_recovery_exercises",
            "deterministic_operational_go_live_readiness",
            "immutable_operational_acceptance_evidence_pack",
            "human_only_operational_readiness_certification",
        ],
        "authority": OPERATIONAL_READINESS_AUTHORITY,
        "traceability": "Release 107 human release candidate -> Release 108 human security certification -> performance/resilience/DR drills -> deterministic operational gates -> human operational readiness certification -> separate human production promotion",
    }
