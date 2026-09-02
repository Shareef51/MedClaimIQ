from __future__ import annotations
import hashlib, json
from typing import Any
from app.domain.production_security_privacy_compliance_red_team import REQUIRED_SECURITY_RELEASE_GATES, NON_WAIVABLE_CATEGORIES, NON_WAIVABLE_SEVERITIES

def version_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _ok(v: Any) -> bool:
    if isinstance(v, bool): return v
    return str(v or "").lower() in {"pass","passed","ok","healthy","success","succeeded","validated","complete","blocked_as_expected","denied_as_expected"}

def _failed_cases(cases, required_fields):
    failed=[]
    for c in cases:
        if not all(bool(c.get(k)) for k in required_fields): failed.append(c.get("case_id") or "unnamed")
    return failed

def assess_cross_tenant_penetration(payload):
    cases=payload.get("cases",[]); required={"sql","vector","cache","object_storage","events","rag","agents","mcp"}; observed={str(c.get("surface")) for c in cases}
    violations=[]
    for c in cases:
        cross=c.get("source_tenant_id")!=c.get("target_tenant_id")
        ok=bool(c.get("access_denied")) and not bool(c.get("data_disclosed")) and bool(c.get("audit_emitted"))
        if cross and not ok: violations.append(c.get("case_id") or "unnamed")
    missing=sorted(required-observed)
    return {"violations":violations,"missing_surfaces":missing,"cross_tenant_penetration_passed":bool(cases) and not violations and not missing}

def assess_authorization_abuse(payload):
    cases=payload.get("cases",[]); required={"expired_token","wrong_audience","wrong_issuer","algorithm_confusion","role_escalation","idor","session_replay","confused_deputy"}; observed={str(c.get("attack_type")) for c in cases}
    failures=[]
    for c in cases:
        if not bool(c.get("denied")) or not bool(c.get("audit_emitted")) or bool(c.get("privilege_granted")): failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_attack_types":sorted(required-observed),"authorization_abuse_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_prompt_injection(payload):
    cases=payload.get("cases",[]); required={"direct","indirect_document","retrieved_content","tool_output","multimodal_hidden_instruction"}; observed={str(c.get("injection_type")) for c in cases}
    failures=[]
    for c in cases:
        ok=bool(c.get("detected_or_neutralized")) and bool(c.get("untrusted_context_preserved")) and not bool(c.get("system_prompt_disclosed")) and not bool(c.get("unauthorized_action"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_injection_types":sorted(required-observed),"prompt_injection_defense_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_rag_poisoning_exfiltration(payload):
    cases=payload.get("cases",[]); required={"poisoned_chunk","cross_tenant_chunk","citation_swap","metadata_bypass","sensitive_query_exfiltration"}; observed={str(c.get("attack_type")) for c in cases}
    failures=[]
    for c in cases:
        ok=bool(c.get("blocked_or_quarantined")) and bool(c.get("tenant_filter_enforced")) and bool(c.get("citation_integrity_preserved")) and not bool(c.get("sensitive_data_disclosed"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_attack_types":sorted(required-observed),"rag_poisoning_exfiltration_defense_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_mcp_tool_abuse(payload):
    cases=payload.get("cases",[]); required={"unknown_tool","scope_escalation","argument_injection","approval_bypass","replay","cross_tenant_tool_call"}; observed={str(c.get("attack_type")) for c in cases}
    failures=[]
    for c in cases:
        ok=bool(c.get("denied")) and bool(c.get("policy_checked")) and bool(c.get("audit_emitted")) and not bool(c.get("side_effect_executed"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_attack_types":sorted(required-observed),"mcp_tool_abuse_defense_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_agent_privilege_boundary(payload):
    cases=payload.get("cases",[]); failures=[]
    for c in cases:
        ok=bool(c.get("authority_boundary_enforced")) and bool(c.get("human_approval_preserved")) and not bool(c.get("unauthorized_state_transition")) and not bool(c.get("financial_authority_exercised"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"agent_privilege_boundary_passed":bool(cases) and not failures}

def assess_phi_pii_leakage(payload):
    cases=payload.get("cases",[]); required={"logs","metrics","traces","llm_prompt","llm_output","audit_export","error_response"}; observed={str(c.get("surface")) for c in cases}; failures=[]
    for c in cases:
        ok=bool(c.get("redacted_or_blocked")) and bool(c.get("minimum_necessary")) and not bool(c.get("raw_sensitive_data_externalized"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_surfaces":sorted(required-observed),"phi_pii_leakage_prevention_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_supply_chain(payload):
    secret_count=int(payload.get("secret_findings",0)); critical=int(payload.get("critical_vulnerabilities",0)); high=int(payload.get("high_vulnerabilities",0));
    checks={
      "secret_scanning": bool(payload.get("secret_scan_passed")) and secret_count==0,
      "dependency_vulnerability_scan": bool(payload.get("dependency_scan_passed")) and critical==0 and high==0,
      "sbom_and_provenance": bool(payload.get("sbom_present")) and bool(payload.get("provenance_present")) and bool(payload.get("images_signed")),
      "container_security": bool(payload.get("container_scan_passed")) and bool(payload.get("non_root_containers")),
      "iac_security": bool(payload.get("iac_scan_passed")) and bool(payload.get("network_policies_present")) and bool(payload.get("secrets_externalized")),
    }
    return {**checks,"secret_findings":secret_count,"critical_vulnerabilities":critical,"high_vulnerabilities":high,"supply_chain_passed":all(checks.values())}

def assess_api_fuzzing(payload):
    cases=payload.get("cases",[]); failures=[]
    for c in cases:
        ok=not bool(c.get("server_crash")) and not bool(c.get("stack_trace_leaked")) and bool(c.get("bounded_response")) and bool(c.get("authz_preserved")) and bool(c.get("tenant_scope_preserved"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"api_fuzzing_passed":bool(cases) and not failures}

def assess_audit_tamper(payload):
    cases=payload.get("cases",[]); required={"record_mutation","record_deletion","record_insertion","reordering","signature_mismatch"}; observed={str(c.get("tamper_type")) for c in cases}; failures=[]
    for c in cases:
        if not bool(c.get("tamper_detected")) or not bool(c.get("verification_failed_closed")): failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_tamper_types":sorted(required-observed),"audit_integrity_passed":bool(cases) and not failures and required.issubset(observed)}

def assess_adversarial_multimodal(payload):
    cases=payload.get("cases",[]); required={"ocr_hidden_instruction","pdf_overlay","image_steganographic_instruction","audio_prompt_injection","video_keyframe_mismatch","metadata_spoofing"}; observed={str(c.get("attack_type")) for c in cases}; failures=[]
    for c in cases:
        ok=bool(c.get("content_treated_untrusted")) and bool(c.get("instruction_neutralized")) and bool(c.get("provenance_preserved")) and not bool(c.get("unauthorized_action"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_cases":failures,"missing_attack_types":sorted(required-observed),"adversarial_multimodal_passed":bool(cases) and not failures and required.issubset(observed)}

def validate_waiver_eligibility(payload):
    sev=str(payload.get("severity","")).lower(); cat=str(payload.get("category","")).lower();
    eligible=sev not in NON_WAIVABLE_SEVERITIES and cat not in NON_WAIVABLE_CATEGORIES and bool(payload.get("compensating_controls")) and bool(payload.get("expires_at")) and bool(payload.get("evidence_refs"))
    return {"waiver_eligible":eligible,"severity_non_waivable":sev in NON_WAIVABLE_SEVERITIES,"category_non_waivable":cat in NON_WAIVABLE_CATEGORIES}

def security_release_readiness(payload):
    gates=payload.get("gates",{}); normalized={g:_ok(gates.get(g)) for g in REQUIRED_SECURITY_RELEASE_GATES}; blockers=[g for g,v in normalized.items() if not v]
    findings=payload.get("findings",[]); open_critical_high=[]; open_nonwaivable=[]; unwaived=[]
    approved_waivers={str(w.get("finding_id")) for w in payload.get("approved_waivers",[]) if w.get("approved") and not w.get("expired")}
    for f in findings:
        if str(f.get("status","open")).lower() in {"closed","remediated","false_positive"}: continue
        fid=str(f.get("finding_id") or "unnamed"); sev=str(f.get("severity","")).lower(); cat=str(f.get("category","")).lower()
        if sev in NON_WAIVABLE_SEVERITIES: open_critical_high.append(fid)
        if cat in NON_WAIVABLE_CATEGORIES: open_nonwaivable.append(fid)
        if fid not in approved_waivers: unwaived.append(fid)
    evidence_complete=bool(payload.get("release107_release_candidate_decision_version_id")) and bool(payload.get("evidence_refs")) and bool(payload.get("sbom_ref")) and bool(payload.get("security_report_ref"))
    ready=not blockers and not open_critical_high and not open_nonwaivable and not unwaived and evidence_complete
    return {"required_gates":normalized,"blocking_gates":blockers,"open_critical_high_findings":open_critical_high,"open_nonwaivable_findings":open_nonwaivable,"open_unwaived_findings":unwaived,"evidence_complete":evidence_complete,"security_readiness_score":round(sum(normalized.values())/len(normalized)*100,2),"release_security_ready":ready,"automated_security_certification":False,"automated_production_promotion":False}

def compliance_evidence_pack(payload):
    readiness=security_release_readiness(payload)
    pack={"pack_type":"release_security_compliance_evidence","candidate_version":payload.get("candidate_version"),"release107_release_candidate_decision_version_id":payload.get("release107_release_candidate_decision_version_id"),"controls":payload.get("controls",[]),"findings":payload.get("findings",[]),"waivers":payload.get("approved_waivers",[]),"evidence_refs":payload.get("evidence_refs",[]),"readiness":readiness,"frameworks":payload.get("frameworks",["HIPAA Security Rule technical safeguards","NIST SP 800-66 Rev.2","OWASP ASVS 5.0","OWASP LLM Top 10","SLSA provenance principles","CycloneDX SBOM"])}
    pack["evidence_pack_hash"]=version_hash(pack); return pack
