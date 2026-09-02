from __future__ import annotations
import hashlib, json
from typing import Any
from app.domain.production_end_to_end_system_integration import REQUIRED_CROSS_DOMAIN_STAGES, REQUIRED_RELEASE_GATES

def version_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _status_ok(value: Any) -> bool:
    if isinstance(value, bool): return value
    return str(value or "").lower() in {"pass", "passed", "ok", "healthy", "success", "succeeded", "validated", "complete"}

def assess_golden_journey(payload: dict[str, Any]) -> dict[str, Any]:
    stages = payload.get("stages", [])
    by_name = {str(x.get("name")): x for x in stages}
    missing = [x for x in REQUIRED_CROSS_DOMAIN_STAGES if x not in by_name]
    failed = [x for x in REQUIRED_CROSS_DOMAIN_STAGES if x in by_name and not _status_ok(by_name[x].get("status"))]
    evidence_missing = [x for x in REQUIRED_CROSS_DOMAIN_STAGES if x in by_name and not by_name[x].get("evidence_refs")]
    tenant_ids = {str(x.get("tenant_id")) for x in stages if x.get("tenant_id")}
    expected_tenant = payload.get("tenant_id")
    tenant_consistent = not tenant_ids or tenant_ids == {str(expected_tenant)}
    citations_valid = all(bool(x.get("citations_validated", True)) for x in stages)
    human_authority_preserved = bool(payload.get("human_final_decision_recorded", False)) and not bool(payload.get("automated_final_claim_decision", False))
    passed = not missing and not failed and not evidence_missing and tenant_consistent and citations_valid and human_authority_preserved
    return {
        "required_stage_count": len(REQUIRED_CROSS_DOMAIN_STAGES),
        "observed_stage_count": len(by_name),
        "missing_stages": missing,
        "failed_stages": failed,
        "stages_missing_evidence": evidence_missing,
        "tenant_consistent": tenant_consistent,
        "citations_validated": citations_valid,
        "human_final_authority_preserved": human_authority_preserved,
        "golden_journey_passed": passed,
    }

def assess_api_contract_regression(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("checks", [])
    required = {"openapi_schema", "backward_compatibility", "request_response_contracts", "auth_error_contracts", "idempotency_contracts"}
    by_name = {str(x.get("name")): x for x in checks}
    missing = sorted(required - set(by_name))
    failed = sorted(name for name, item in by_name.items() if name in required and not _status_ok(item.get("status")))
    breaking_changes = [x for x in payload.get("breaking_changes", []) if not x.get("approved", False)]
    return {
        "missing_contract_checks": missing,
        "failed_contract_checks": failed,
        "unapproved_breaking_changes": breaking_changes,
        "api_contract_regression_passed": not missing and not failed and not breaking_changes,
    }

def assess_tenant_isolation(payload: dict[str, Any]) -> dict[str, Any]:
    cases = payload.get("cases", [])
    violations=[]
    for case in cases:
        if case.get("source_tenant_id") != case.get("target_tenant_id"):
            denied = bool(case.get("access_denied"))
            leaked = bool(case.get("data_leak_detected"))
            if not denied or leaked:
                violations.append(case.get("case_id") or "unnamed")
    required_surfaces = set(payload.get("required_surfaces", ["sql", "vector", "cache", "object_storage", "events", "rag", "agents"]))
    observed = {str(x.get("surface")) for x in cases}
    missing_surfaces = sorted(required_surfaces - observed)
    passed = bool(cases) and not violations and not missing_surfaces
    return {"tenant_isolation_violations": violations, "missing_isolation_surfaces": missing_surfaces, "tenant_isolation_passed": passed}

def assess_workflow_recovery(payload: dict[str, Any]) -> dict[str, Any]:
    cases=payload.get("cases", [])
    failures=[]
    for c in cases:
        ok = bool(c.get("checkpoint_persisted")) and bool(c.get("resume_succeeded")) and bool(c.get("idempotent_replay")) and not bool(c.get("duplicate_side_effect"))
        if c.get("human_interrupt_required"): ok = ok and bool(c.get("human_interrupt_preserved"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    required_types={"worker_restart","provider_timeout","human_interrupt_resume","duplicate_delivery"}
    observed={str(c.get("type")) for c in cases}
    missing=sorted(required_types-observed)
    return {"failed_recovery_cases": failures, "missing_recovery_case_types": missing, "durable_workflow_recovery_passed": bool(cases) and not failures and not missing}

def assess_event_sse_integrity(payload: dict[str, Any]) -> dict[str, Any]:
    cases=payload.get("cases", [])
    failures=[]
    for c in cases:
        ok = bool(c.get("monotonic_sequence")) and bool(c.get("reconnect_replay_ok")) and bool(c.get("tenant_scoped")) and not bool(c.get("duplicate_business_effect"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    return {"failed_event_stream_cases": failures, "event_sse_integrity_passed": bool(cases) and not failures}

def assess_failure_injection(payload: dict[str, Any]) -> dict[str, Any]:
    cases=payload.get("cases", [])
    failures=[]
    for c in cases:
        ok = bool(c.get("bounded_retry")) and bool(c.get("fallback_or_fail_closed")) and bool(c.get("audit_emitted")) and bool(c.get("recovered_or_escalated"))
        if c.get("high_risk"): ok = ok and bool(c.get("human_escalation_preserved"))
        if not ok: failures.append(c.get("case_id") or "unnamed")
    required={"postgres","redis","vector_store","object_storage","llm_provider","mcp_dependency","event_backbone"}
    observed={str(c.get("dependency")) for c in cases}
    missing=sorted(required-observed)
    return {"failed_failure_injection_cases": failures, "missing_dependency_failures": missing, "failure_injection_resilience_passed": bool(cases) and not failures and not missing}

def assess_migration_chain(payload: dict[str, Any]) -> dict[str, Any]:
    revisions=payload.get("revisions", [])
    by_rev={str(x.get("revision")): x for x in revisions if x.get("revision")}
    down_refs={str(x.get("down_revision")) for x in revisions if x.get("down_revision")}
    heads=sorted(set(by_rev)-down_refs)
    missing_predecessors=sorted({str(x.get("down_revision")) for x in revisions if x.get("down_revision") and str(x.get("down_revision")) not in by_rev})
    duplicate_revisions=len(by_rev)!=len(revisions)
    expected_head=payload.get("expected_head")
    head_ok=(not expected_head) or heads==[expected_head]
    return {"heads": heads, "missing_predecessors": missing_predecessors, "duplicate_revisions": duplicate_revisions, "expected_head": expected_head, "migration_chain_integrity_passed": bool(revisions) and len(heads)==1 and not missing_predecessors and not duplicate_revisions and head_ok}

def release_candidate_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    gates=payload.get("gates", {})
    normalized={name: _status_ok(gates.get(name)) for name in REQUIRED_RELEASE_GATES}
    blockers=[name for name, ok in normalized.items() if not ok]
    scores=payload.get("quality_scores", {})
    min_quality=float(payload.get("minimum_quality_score", 0.90))
    quality_failures=sorted(k for k,v in scores.items() if float(v)<min_quality)
    evidence_complete=bool(payload.get("evidence_refs")) and bool(payload.get("release_manifest_ref"))
    ready=not blockers and not quality_failures and evidence_complete
    return {"required_gates": normalized, "blocking_gates": blockers, "quality_score_failures": quality_failures, "evidence_complete": evidence_complete, "readiness_score": round((sum(normalized.values())/len(normalized))*100,2), "release_candidate_ready": ready, "automated_release_candidate_declaration": False, "automated_production_promotion": False}

def consolidated_readiness_report(payload: dict[str, Any]) -> dict[str, Any]:
    readiness=release_candidate_readiness(payload)
    return {"report_type":"production_release_candidate_readiness", **readiness, "risk_summary":payload.get("risk_summary",[]), "open_findings":payload.get("open_findings",[]), "evidence_refs":payload.get("evidence_refs",[]), "report_hash":version_hash({**payload, **readiness})}
