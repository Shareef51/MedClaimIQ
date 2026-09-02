from __future__ import annotations
import hashlib, json
from typing import Any
from app.domain.production_go_live_governance_final_release_certification import REQUIRED_FINAL_GATES, NON_BYPASSABLE_RELEASE_RISKS, REQUIRED_POST_DEPLOY_SURFACES

def version_hash(payload:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def validate_upstream_certifications(p):
    refs={"release107_release_candidate":p.get("release107_release_candidate_decision_version_id"),"release108_security_certification":p.get("release108_release_security_certification_version_id"),"release109_operational_certification":p.get("release109_operational_readiness_certification_version_id")}
    missing=[k for k,v in refs.items() if not v]
    return {"references":refs,"missing_upstream_certifications":missing,"upstream_human_certifications_valid":not missing}

def assess_release_manifest(p):
    required=["release_id","candidate_version","git_commit_sha","image_digest","sbom_digest","migration_head","configuration_fingerprint","evidence_refs"]
    missing=[x for x in required if not p.get(x)]
    immutable=bool(p.get("git_commit_sha")) and str(p.get("image_digest","")).startswith("sha256:") and bool(p.get("sbom_digest"))
    expected=p.get("expected_migration_head","0105_final_production_go_live")
    migration_ok=p.get("migration_head")==expected
    return {"missing_manifest_fields":missing,"immutable_artifact_identity":immutable,"migration_head_matches":migration_ok,"release_manifest_integrity_passed":not missing and immutable and migration_ok}

def assess_deployment_preflight(p):
    checks=p.get("checks",[]); failed=[]
    for c in checks:
        if not (c.get("passed") and c.get("evidence_ref")): failed.append(c.get("check_id","unknown"))
    required=set(p.get("required_checks",["database_connectivity","migration_preflight","backup_checkpoint","secrets_configuration","tenant_isolation","rollback_artifact","change_window","gitops_plan"]))
    present={c.get("check_id") for c in checks}; missing=sorted(required-present)
    return {"failed_checks":failed,"missing_checks":missing,"deployment_preflight_passed":bool(checks) and not failed and not missing}

def assess_canary_progressive_rollout(p):
    stages=p.get("stages",[]); failed=[]
    for s in stages:
        good=bool(s.get("slo_passed")) and bool(s.get("error_budget_preserved")) and bool(s.get("tenant_isolation_preserved")) and bool(s.get("data_integrity_preserved")) and not bool(s.get("sev1_or_critical_security_incident"))
        if not good: failed.append(s.get("stage","unknown"))
    rollback_ready=bool(p.get("rollback_ready")) and bool(p.get("rollback_artifact_verified"))
    return {"failed_stages":failed,"rollback_ready":rollback_ready,"canary_progressive_rollout_passed":bool(stages) and not failed and rollback_ready}

def assess_post_deployment_verification(p):
    surfaces=p.get("surfaces",[]); by={str(x.get("surface")):x for x in surfaces}; missing=[x for x in REQUIRED_POST_DEPLOY_SURFACES if x not in by]; failed=[]
    for name in REQUIRED_POST_DEPLOY_SURFACES:
        x=by.get(name)
        if x and not (x.get("healthy") and x.get("evidence_ref") and x.get("tenant_isolation_preserved",True) and x.get("data_integrity_preserved",True)): failed.append(name)
    smoke=bool(p.get("smoke_tests_passed")) and bool(p.get("synthetic_claim_journey_passed")) and bool(p.get("ai_rag_agent_verification_passed"))
    return {"missing_surfaces":missing,"failed_surfaces":failed,"smoke_and_synthetic_passed":smoke,"post_deployment_verification_passed":not missing and not failed and smoke}

def assess_hypercare(p):
    return {"command_center_ready":all(bool(p.get(x)) for x in ["incident_commander_assigned","oncall_routes_verified","dashboards_verified","rollback_owner_assigned","communications_plan_ready"]),"slo_window_passed":bool(p.get("slo_window_passed")),"open_sev1":int(p.get("open_sev1",0)),"open_sev2":int(p.get("open_sev2",0)),"hypercare_ready":all(bool(p.get(x)) for x in ["incident_commander_assigned","oncall_routes_verified","dashboards_verified","rollback_owner_assigned","communications_plan_ready"]) and int(p.get("open_sev1",0))==0}

def final_go_live_readiness(p):
    upstream=validate_upstream_certifications(p); gates=dict(p.get("gates",{}))
    for k in ("release107_release_candidate","release108_security_certification","release109_operational_certification"): gates[k]=upstream["references"][k] is not None
    missing=[g for g in REQUIRED_FINAL_GATES if not gates.get(g,False)]
    risks=[]
    for r in p.get("open_release_risks",[]):
        if str(r.get("status","open")).lower() not in {"closed","resolved","accepted_closed"}:
            cat=str(r.get("category","")); sev=str(r.get("severity","")).lower()
            if cat in NON_BYPASSABLE_RELEASE_RISKS or sev in {"sev1","critical"}: risks.append(r.get("risk_id","unknown"))
    ready=not missing and not risks and upstream["upstream_human_certifications_valid"]
    return {**upstream,"missing_final_gates":missing,"non_bypassable_open_risks":risks,"final_go_live_ready":ready,"automated_go_live_approval":False,"automated_production_promotion":False}

def final_release_evidence_bundle(p):
    readiness=final_go_live_readiness(p); body={"release_id":p.get("release_id"),"candidate_version":p.get("candidate_version"),"upstream":readiness["references"],"gates":p.get("gates",{}),"evidence_refs":sorted(set(p.get("evidence_refs",[]))),"readiness":readiness}
    return {**body,"evidence_bundle_hash":version_hash(body),"immutable":True}
