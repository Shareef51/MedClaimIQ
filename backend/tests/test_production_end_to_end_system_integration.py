from pathlib import Path
import pytest
from app.domain.production_end_to_end_system_integration import REQUIRED_CROSS_DOMAIN_STAGES, REQUIRED_RELEASE_GATES, RELEASE_CANDIDATE_HARDENING_AUTHORITY
from app.evaluation.production_end_to_end_system_integration import *
from app.services.production_end_to_end_system_integration import ProductionEndToEndSystemIntegrationService
ROOT=Path(__file__).resolve().parents[2]

def _journey():
    return {"journey_id":"j1","tenant_id":"t1","human_final_decision_recorded":True,"automated_final_claim_decision":False,"stages":[{"name":x,"status":"passed","tenant_id":"t1","evidence_refs":[f"e:{x}"],"citations_validated":True} for x in REQUIRED_CROSS_DOMAIN_STAGES]}

def test_cross_domain_golden_journey_requires_every_stage_evidence_and_human_authority():
    ok=assess_golden_journey(_journey()); assert ok["golden_journey_passed"] is True
    bad=_journey(); bad["stages"][3]["evidence_refs"]=[]; assert assess_golden_journey(bad)["golden_journey_passed"] is False
    auto=_journey(); auto["automated_final_claim_decision"]=True; assert assess_golden_journey(auto)["human_final_authority_preserved"] is False

def test_tenant_recovery_events_and_failure_injection_are_blocking_controls():
    iso=assess_tenant_isolation({"cases":[{"case_id":s,"surface":s,"source_tenant_id":"a","target_tenant_id":"b","access_denied":True,"data_leak_detected":False} for s in ["sql","vector","cache","object_storage","events","rag","agents"]]}); assert iso["tenant_isolation_passed"]
    rec=assess_workflow_recovery({"cases":[{"case_id":t,"type":t,"checkpoint_persisted":True,"resume_succeeded":True,"idempotent_replay":True,"duplicate_side_effect":False,"human_interrupt_required":t=="human_interrupt_resume","human_interrupt_preserved":True} for t in ["worker_restart","provider_timeout","human_interrupt_resume","duplicate_delivery"]]}); assert rec["durable_workflow_recovery_passed"]
    ev=assess_event_sse_integrity({"cases":[{"case_id":"sse","monotonic_sequence":True,"reconnect_replay_ok":True,"tenant_scoped":True,"duplicate_business_effect":False}]}); assert ev["event_sse_integrity_passed"]
    deps=["postgres","redis","vector_store","object_storage","llm_provider","mcp_dependency","event_backbone"]
    fi=assess_failure_injection({"cases":[{"case_id":d,"dependency":d,"bounded_retry":True,"fallback_or_fail_closed":True,"audit_emitted":True,"recovered_or_escalated":True,"high_risk":d in {"llm_provider","mcp_dependency"},"human_escalation_preserved":True} for d in deps]}); assert fi["failure_injection_resilience_passed"]

def test_release_candidate_gate_is_deterministic_and_cannot_bypass_failed_gate_or_quality():
    payload={"gates":{x:True for x in REQUIRED_RELEASE_GATES},"quality_scores":{"groundedness":.96,"citation_precision":.98},"minimum_quality_score":.9,"evidence_refs":["e1"],"release_manifest_ref":"manifest"}
    assert release_candidate_readiness(payload)["release_candidate_ready"] is True
    payload["gates"]["tenant_isolation"]=False; result=release_candidate_readiness(payload); assert result["release_candidate_ready"] is False and "tenant_isolation" in result["blocking_gates"]
    assert result["automated_production_promotion"] is False

def test_release_candidate_declaration_is_human_only_and_preserves_production_approval():
    assert RELEASE_CANDIDATE_HARDENING_AUTHORITY["ai_can_declare_release_candidate"] is False
    assert RELEASE_CANDIDATE_HARDENING_AUTHORITY["ai_can_promote_to_production"] is False
    svc=ProductionEndToEndSystemIntegrationService(None,"tenant-a")
    readiness={"release_candidate_ready":True}
    with pytest.raises(PermissionError): svc.decide_candidate("agent",{"actor_role":"ai_agent","decision":"declare_candidate","integration_run_version_id":"r1","readiness":readiness,"rationale":"x","evidence_refs":["e"]})
    decision=svc.decide_candidate("human-1",{"actor_role":"release_manager","decision":"declare_candidate","integration_run_version_id":"r1","readiness":readiness,"rationale":"all gates passed","evidence_refs":["e"]})
    assert decision["human_decision"] is True and decision["automated_production_promotion"] is False and decision["immutable"] is True
