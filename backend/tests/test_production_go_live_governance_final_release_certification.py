import pytest
from app.domain.production_go_live_governance_final_release_certification import *
from app.evaluation.production_go_live_governance_final_release_certification import *
from app.services.production_go_live_governance_final_release_certification import ProductionGoLiveGovernanceFinalReleaseCertificationService

def good_ready(): return {"release_id":"medclaimiq-110","candidate_version":"v110","release107_release_candidate_decision_version_id":"rc107","release108_release_security_certification_version_id":"sec108","release109_operational_readiness_certification_version_id":"ops109","gates":{x:True for x in REQUIRED_FINAL_GATES},"open_release_risks":[],"evidence_refs":["final-pack.json"]}

def test_final_gate_requires_three_human_upstream_certifications_and_non_bypassable_risks():
    p=good_ready(); assert final_go_live_readiness(p)["final_go_live_ready"]
    p.pop("release108_release_security_certification_version_id"); assert not final_go_live_readiness(p)["final_go_live_ready"]
    p=good_ready(); p["open_release_risks"]=[{"risk_id":"R1","category":"tenant_isolation_failure","severity":"critical","status":"open"}]; assert not final_go_live_readiness(p)["final_go_live_ready"]

def test_manifest_preflight_canary_and_post_deploy_are_fail_closed():
    m={"release_id":"r","candidate_version":"v","git_commit_sha":"a"*40,"image_digest":"sha256:"+"b"*64,"sbom_digest":"c"*64,"migration_head":"0105_final_production_go_live","configuration_fingerprint":"d"*64,"evidence_refs":["x"]}; assert assess_release_manifest(m)["release_manifest_integrity_passed"]
    checks=[{"check_id":x,"passed":True,"evidence_ref":"e"} for x in ["database_connectivity","migration_preflight","backup_checkpoint","secrets_configuration","tenant_isolation","rollback_artifact","change_window","gitops_plan"]]; assert assess_deployment_preflight({"checks":checks})["deployment_preflight_passed"]
    assert assess_canary_progressive_rollout({"stages":[{"stage":"5%","slo_passed":True,"error_budget_preserved":True,"tenant_isolation_preserved":True,"data_integrity_preserved":True,"sev1_or_critical_security_incident":False}],"rollback_ready":True,"rollback_artifact_verified":True})["canary_progressive_rollout_passed"]
    surfaces=[{"surface":x,"healthy":True,"evidence_ref":"e","tenant_isolation_preserved":True,"data_integrity_preserved":True} for x in REQUIRED_POST_DEPLOY_SURFACES]; assert assess_post_deployment_verification({"surfaces":surfaces,"smoke_tests_passed":True,"synthetic_claim_journey_passed":True,"ai_rag_agent_verification_passed":True})["post_deployment_verification_passed"]

def test_human_only_go_live_deployment_and_final_certification_chain():
    assert FINAL_GO_LIVE_AUTHORITY["ai_can_approve_go_live"] is False
    svc=ProductionGoLiveGovernanceFinalReleaseCertificationService(None,"tenant-a")
    base=good_ready()|{"actor_role":"release_engineer","git_commit_sha":"a"*40,"image_digest":"sha256:"+"b"*64,"sbom_digest":"c"*64,"migration_head":"0105_final_production_go_live","configuration_fingerprint":"d"*64}
    manifest=svc.create_manifest("release-1",base); assert manifest["immutable"]
    with pytest.raises(PermissionError): svc.approve_go_live("agent",good_ready()|{"actor_role":"ai_agent","final_release_manifest_version_id":manifest["final_release_manifest_version_id"],"decision":"approve","rationale":"x"})
    approval=svc.approve_go_live("cto-1",good_ready()|{"actor_role":"chief_technology_officer","final_release_manifest_version_id":manifest["final_release_manifest_version_id"],"decision":"approve","rationale":"all final gates pass"}); assert approval["human_decision"] and not approval["automated_production_promotion"]
    surfaces=[{"surface":x,"healthy":True,"evidence_ref":"e","tenant_isolation_preserved":True,"data_integrity_preserved":True} for x in REQUIRED_POST_DEPLOY_SURFACES]; v=assess_post_deployment_verification({"surfaces":surfaces,"smoke_tests_passed":True,"synthetic_claim_journey_passed":True,"ai_rag_agent_verification_passed":True})
    dep=svc.record_deployment_verification("sre-1",{"actor_role":"site_reliability_engineer","release_id":"medclaimiq-110","candidate_version":"v110","final_release_manifest_version_id":manifest["final_release_manifest_version_id"],"go_live_approval_version_id":approval["go_live_approval_version_id"],"environment":"production","verification":v,"evidence_refs":["deploy.json"]}); assert dep["human_executed"]
    cert=svc.certify_final_release("cto-2",{"actor_role":"final_release_certifier","release_id":"medclaimiq-110","candidate_version":"v110","release107_release_candidate_decision_version_id":"rc107","release108_release_security_certification_version_id":"sec108","release109_operational_readiness_certification_version_id":"ops109","final_release_manifest_version_id":manifest["final_release_manifest_version_id"],"go_live_approval_version_id":approval["go_live_approval_version_id"],"deployment_verification_version_id":dep["deployment_verification_version_id"],"decision":"certify","rationale":"deployment verified","evidence_refs":["final.json"]}); assert cert["human_decision"] and cert["immutable"]

def test_hypercare_closure_is_separate_human_decision():
    svc=ProductionGoLiveGovernanceFinalReleaseCertificationService(None,"tenant-a"); p={"actor_role":"operations_director","release_id":"r","final_release_certification_version_id":"cert110","decision":"close","rationale":"stable","evidence_refs":["slo.json"],"incident_commander_assigned":True,"oncall_routes_verified":True,"dashboards_verified":True,"rollback_owner_assigned":True,"communications_plan_ready":True,"slo_window_passed":True,"open_sev1":0,"open_sev2":0}; c=svc.close_hypercare("ops-1",p); assert c["human_decision"] and not c["automated_closure"]
    p["open_sev1"]=1
    with pytest.raises(ValueError): svc.close_hypercare("ops-1",p)
