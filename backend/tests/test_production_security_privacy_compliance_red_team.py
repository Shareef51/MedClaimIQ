import pytest
from pathlib import Path
from app.domain.production_security_privacy_compliance_red_team import *
from app.evaluation.production_security_privacy_compliance_red_team import *
from app.services.production_security_privacy_compliance_red_team import ProductionSecurityPrivacyComplianceRedTeamService

def test_cross_tenant_auth_prompt_rag_mcp_and_agent_boundaries_are_blocking():
    surfaces=["sql","vector","cache","object_storage","events","rag","agents","mcp"]
    assert assess_cross_tenant_penetration({"cases":[{"case_id":s,"surface":s,"source_tenant_id":"a","target_tenant_id":"b","access_denied":True,"data_disclosed":False,"audit_emitted":True} for s in surfaces]})["cross_tenant_penetration_passed"]
    attacks=["expired_token","wrong_audience","wrong_issuer","algorithm_confusion","role_escalation","idor","session_replay","confused_deputy"]
    assert assess_authorization_abuse({"cases":[{"case_id":x,"attack_type":x,"denied":True,"audit_emitted":True,"privilege_granted":False} for x in attacks]})["authorization_abuse_passed"]
    injections=["direct","indirect_document","retrieved_content","tool_output","multimodal_hidden_instruction"]
    assert assess_prompt_injection({"cases":[{"case_id":x,"injection_type":x,"detected_or_neutralized":True,"untrusted_context_preserved":True,"system_prompt_disclosed":False,"unauthorized_action":False} for x in injections]})["prompt_injection_defense_passed"]
    rag=["poisoned_chunk","cross_tenant_chunk","citation_swap","metadata_bypass","sensitive_query_exfiltration"]
    assert assess_rag_poisoning_exfiltration({"cases":[{"case_id":x,"attack_type":x,"blocked_or_quarantined":True,"tenant_filter_enforced":True,"citation_integrity_preserved":True,"sensitive_data_disclosed":False} for x in rag]})["rag_poisoning_exfiltration_defense_passed"]
    mcp=["unknown_tool","scope_escalation","argument_injection","approval_bypass","replay","cross_tenant_tool_call"]
    assert assess_mcp_tool_abuse({"cases":[{"case_id":x,"attack_type":x,"denied":True,"policy_checked":True,"audit_emitted":True,"side_effect_executed":False} for x in mcp]})["mcp_tool_abuse_defense_passed"]
    assert assess_agent_privilege_boundary({"cases":[{"case_id":"a","authority_boundary_enforced":True,"human_approval_preserved":True,"unauthorized_state_transition":False,"financial_authority_exercised":False}]})["agent_privilege_boundary_passed"]

def test_privacy_supply_chain_api_audit_and_multimodal_gates():
    surfaces=["logs","metrics","traces","llm_prompt","llm_output","audit_export","error_response"]
    assert assess_phi_pii_leakage({"cases":[{"case_id":s,"surface":s,"redacted_or_blocked":True,"minimum_necessary":True,"raw_sensitive_data_externalized":False} for s in surfaces]})["phi_pii_leakage_prevention_passed"]
    supply={"secret_scan_passed":True,"secret_findings":0,"dependency_scan_passed":True,"critical_vulnerabilities":0,"high_vulnerabilities":0,"sbom_present":True,"provenance_present":True,"images_signed":True,"container_scan_passed":True,"non_root_containers":True,"iac_scan_passed":True,"network_policies_present":True,"secrets_externalized":True}
    assert assess_supply_chain(supply)["supply_chain_passed"]
    assert assess_api_fuzzing({"cases":[{"case_id":"f","server_crash":False,"stack_trace_leaked":False,"bounded_response":True,"authz_preserved":True,"tenant_scope_preserved":True}]})["api_fuzzing_passed"]
    tamper=["record_mutation","record_deletion","record_insertion","reordering","signature_mismatch"]
    assert assess_audit_tamper({"cases":[{"case_id":x,"tamper_type":x,"tamper_detected":True,"verification_failed_closed":True} for x in tamper]})["audit_integrity_passed"]
    mm=["ocr_hidden_instruction","pdf_overlay","image_steganographic_instruction","audio_prompt_injection","video_keyframe_mismatch","metadata_spoofing"]
    assert assess_adversarial_multimodal({"cases":[{"case_id":x,"attack_type":x,"content_treated_untrusted":True,"instruction_neutralized":True,"provenance_preserved":True,"unauthorized_action":False} for x in mm]})["adversarial_multimodal_passed"]

def test_nonwaivable_findings_and_readiness_are_deterministic():
    assert validate_waiver_eligibility({"severity":"high","category":"other","compensating_controls":["x"],"expires_at":"2026-09-01","evidence_refs":["e"]})["waiver_eligible"] is False
    assert validate_waiver_eligibility({"severity":"medium","category":"cross_tenant_escape","compensating_controls":["x"],"expires_at":"2026-09-01","evidence_refs":["e"]})["waiver_eligible"] is False
    payload={"release107_release_candidate_decision_version_id":"rc1","gates":{x:True for x in REQUIRED_SECURITY_RELEASE_GATES},"findings":[],"approved_waivers":[],"evidence_refs":["e"],"sbom_ref":"sbom","security_report_ref":"report"}
    assert security_release_readiness(payload)["release_security_ready"] is True
    payload["findings"]=[{"finding_id":"F1","severity":"high","category":"other","status":"open"}]
    assert security_release_readiness(payload)["release_security_ready"] is False

def test_waiver_and_release_security_certification_are_human_only():
    assert SECURITY_RED_TEAM_AUTHORITY["ai_can_issue_security_certification"] is False
    svc=ProductionSecurityPrivacyComplianceRedTeamService(None,"tenant-a")
    with pytest.raises(PermissionError): svc.approve_waiver("agent",{"actor_role":"ai_agent","severity":"medium","category":"other"})
    with pytest.raises(ValueError): svc.approve_waiver("ciso",{"actor_role":"chief_information_security_officer","release_id":"r","finding_id":"F","severity":"high","category":"other","rationale":"x","compensating_controls":["c"],"expires_at":"2026-09-01","evidence_refs":["e"]})
    ready={"release_security_ready":True}
    with pytest.raises(PermissionError): svc.certify("agent",{"actor_role":"ai_agent","decision":"certify","release107_release_candidate_decision_version_id":"rc1","security_red_team_run_version_id":"rt1","readiness":ready,"evidence_refs":["e"]})
    cert=svc.certify("human",{"actor_role":"chief_information_security_officer","release_id":"r","candidate_version":"v","decision":"certify","release107_release_candidate_decision_version_id":"rc1","security_red_team_run_version_id":"rt1","readiness":ready,"rationale":"all gates pass","evidence_refs":["e"],"compliance_evidence_pack_hash":"h"})
    assert cert["human_decision"] is True and cert["automated_production_promotion"] is False and cert["immutable"] is True


def test_security_scanner_policies_do_not_hide_entire_docs_or_sample_directories():
    root=Path(__file__).resolve().parents[2]
    g=(root/'.gitleaks.toml').read_text()
    assert 'paths = [' not in g
    s=(root/'.semgrep.yml').read_text()
    assert 'medclaimiq-no-httpx-tls-verification-disable' in s
    assert 'medclaimiq-no-jwt-signature-bypass' in s
    assert 'medclaimiq-no-pickle-deserialization' in s
