from __future__ import annotations

FINAL_GO_LIVE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_assess_release_readiness": True,
    "ai_can_prepare_release_manifest_and_evidence": True,
    "ai_can_monitor_canary_and_hypercare": True,
    "ai_can_recommend_rollback": True,
    "ai_can_approve_go_live": False,
    "ai_can_execute_production_promotion": False,
    "ai_can_issue_final_release_certification": False,
    "ai_can_close_hypercare": False,
    "worker_can_approve_go_live": False,
    "worker_can_promote_to_production": False,
    "release107_human_release_candidate_required": True,
    "release108_human_security_certification_required": True,
    "release109_human_operational_certification_required": True,
    "human_change_window_approval_required": True,
    "human_go_live_approval_required": True,
    "human_deployment_execution_required": True,
    "human_final_release_certification_required": True,
    "human_hypercare_closure_required": True,
    "rollback_must_remain_available": True,
    "tenant_isolation_failure_non_bypassable": True,
    "data_integrity_failure_non_bypassable": True,
    "security_certification_failure_non_bypassable": True,
    "rollback_unavailable_non_bypassable": True,
    "sev1_incident_non_bypassable": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
    "funds_collection_allowed": False,
    "funds_movement_allowed": False,
}

REQUIRED_FINAL_GATES = [
    "release107_release_candidate", "release108_security_certification", "release109_operational_certification",
    "release_manifest_integrity", "change_window_approved", "database_preflight", "gitops_promotion_plan",
    "canary_progressive_rollout", "smoke_synthetic_validation", "ai_rag_agent_post_deploy_verification",
    "production_observability", "rollback_readiness", "hypercare_command_center", "final_audit_evidence_bundle",
]
NON_BYPASSABLE_RELEASE_RISKS = {
    "missing_upstream_human_certification", "tenant_isolation_failure", "data_integrity_failure",
    "phi_pii_exfiltration", "unsafe_model_substitution", "migration_integrity_failure",
    "rollback_unavailable", "sev1_incident", "critical_security_regression",
}
REQUIRED_POST_DEPLOY_SURFACES=["api","frontend","rag","agents","mcp","event_stream","postgresql","redis","vector_store","observability"]

def production_go_live_contract() -> dict:
    return {
        "name":"production_go_live_governance_final_release_certification_deployment_verification_and_hypercare",
        "required_final_gates":REQUIRED_FINAL_GATES,
        "required_post_deploy_surfaces":REQUIRED_POST_DEPLOY_SURFACES,
        "non_bypassable_release_risks":sorted(NON_BYPASSABLE_RELEASE_RISKS),
        "capabilities":[
            "immutable_release_manifest","human_change_window_and_go_live_approval","gitops_production_promotion_governance",
            "database_preflight_and_migration_head_validation","canary_and_progressive_rollout","smoke_and_synthetic_transaction_validation",
            "ai_rag_agent_mcp_post_deployment_verification","rollback_criteria_and_safe_abort","production_observability_and_slo_verification",
            "hypercare_command_center_and_escalation","post_launch_slo_monitoring","immutable_final_audit_evidence_bundle",
            "human_only_final_release_certification","human_only_hypercare_closure","recruiter_and_demo_release_documentation",
        ],
        "authority":FINAL_GO_LIVE_AUTHORITY,
        "traceability":"Release 107 human release candidate -> Release 108 human security certification -> Release 109 human operational certification -> final manifest -> human go-live approval -> human GitOps deployment -> deployment verification -> human final release certification -> hypercare -> human hypercare closure",
    }
