from __future__ import annotations

SECURITY_RED_TEAM_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_generate_adversarial_test_cases": True,
    "ai_can_score_security_controls": True,
    "ai_can_detect_possible_phi_pii_leakage": True,
    "ai_can_detect_prompt_rag_mcp_agent_attack_patterns": True,
    "ai_can_prepare_compliance_evidence_pack": True,
    "ai_can_approve_security_waiver": False,
    "ai_can_accept_security_risk": False,
    "ai_can_issue_security_certification": False,
    "ai_can_promote_to_production": False,
    "worker_can_approve_security_waiver": False,
    "worker_can_issue_security_certification": False,
    "release107_human_release_candidate_decision_required": True,
    "critical_findings_non_waivable": True,
    "high_findings_non_waivable": True,
    "secret_leaks_non_waivable": True,
    "cross_tenant_escape_non_waivable": True,
    "phi_pii_exfiltration_non_waivable": True,
    "human_security_waiver_approval_required": True,
    "human_release_security_certification_required": True,
    "production_promotion_separately_human_approved": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
    "funds_collection_allowed": False,
    "funds_movement_allowed": False,
}

REQUIRED_RED_TEAM_SURFACES = [
    "cross_tenant_penetration",
    "oidc_rbac_authorization_abuse",
    "prompt_injection_indirect_injection",
    "rag_poisoning_data_exfiltration",
    "mcp_tool_abuse",
    "agent_privilege_boundary",
    "phi_pii_leakage",
    "secrets_and_supply_chain",
    "api_fuzzing",
    "audit_tamper_detection",
    "adversarial_multimodal_evidence",
]

REQUIRED_SECURITY_RELEASE_GATES = [
    "cross_tenant_penetration",
    "authorization_abuse",
    "prompt_injection_defense",
    "rag_poisoning_exfiltration_defense",
    "mcp_tool_abuse_defense",
    "agent_privilege_boundary",
    "phi_pii_leakage_prevention",
    "secret_scanning",
    "dependency_vulnerability_scan",
    "sbom_and_provenance",
    "container_security",
    "iac_security",
    "api_fuzzing",
    "audit_integrity",
    "adversarial_multimodal",
    "compliance_evidence_complete",
]

NON_WAIVABLE_CATEGORIES = {
    "cross_tenant_escape", "authorization_bypass", "secret_leak", "phi_exfiltration",
    "pii_exfiltration", "audit_integrity_bypass", "production_tool_privilege_escalation",
}
NON_WAIVABLE_SEVERITIES = {"critical", "high"}


def production_security_privacy_compliance_red_team_contract() -> dict:
    return {
        "name": "production_security_privacy_compliance_red_team_and_release_security_certification",
        "required_red_team_surfaces": REQUIRED_RED_TEAM_SURFACES,
        "required_security_release_gates": REQUIRED_SECURITY_RELEASE_GATES,
        "non_waivable_categories": sorted(NON_WAIVABLE_CATEGORIES),
        "non_waivable_severities": sorted(NON_WAIVABLE_SEVERITIES),
        "capabilities": [
            "cross_tenant_attack_simulation_and_isolation_verification",
            "oidc_jwt_session_rbac_idor_and_confused_deputy_abuse_testing",
            "direct_and_indirect_prompt_injection_resistance",
            "rag_poisoning_retrieval_exfiltration_and_citation_integrity_testing",
            "mcp_argument_policy_approval_scope_and_tool_abuse_testing",
            "agent_privilege_escalation_and_authority_boundary_testing",
            "phi_pii_dlp_logging_tracing_and_output_leakage_validation",
            "gitleaks_semgrep_dependency_sbom_container_and_iac_security_aggregation",
            "api_fuzzing_and_malformed_payload_fail_closed_validation",
            "audit_hash_chain_tamper_detection",
            "adversarial_multimodal_evidence_and_hidden_instruction_testing",
            "bounded_expiring_human_security_waiver_governance",
            "immutable_compliance_evidence_pack_generation",
            "deterministic_release_security_readiness",
            "human_only_release_security_certification",
        ],
        "authority": SECURITY_RED_TEAM_AUTHORITY,
        "traceability": "Release 107 human release candidate -> adversarial security/privacy testing -> findings -> remediation/eligible human waivers -> deterministic security gates -> compliance evidence pack -> human release security certification -> separate human production promotion",
    }
