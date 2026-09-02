from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.production_go_live_governance_final_release_certification import *
MANIFEST_ROLES={"release_engineer","platform_engineer","site_reliability_engineer","tenant_admin"}
GO_LIVE_ROLES={"chief_technology_officer","change_authority","release_approver","executive_release_committee","tenant_admin"}
DEPLOY_ROLES={"release_engineer","platform_engineer","site_reliability_engineer","deployment_operator","tenant_admin"}
FINAL_CERT_ROLES={"chief_technology_officer","final_release_certifier","executive_release_committee","tenant_admin"}
HYPERCARE_ROLES={"site_reliability_engineer","operations_director","incident_commander","tenant_admin"}
HYPERCARE_CLOSE_ROLES={"operations_director","chief_technology_officer","hypercare_certifier","tenant_admin"}
class ProductionGoLiveGovernanceFinalReleaseCertificationService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p): r=dict(p); r["version_hash"]=version_hash(r); r["immutable"]=True; return r
    def manifest_assessment(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_release_manifest(p)}
    def preflight(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_deployment_preflight(p)}
    def canary(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_canary_progressive_rollout(p)}
    def post_deploy(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_post_deployment_verification(p)}
    def hypercare(self,p): return {"tenant_id":self.tenant_id,"monitoring_only":True,**assess_hypercare(p)}
    def readiness(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**final_go_live_readiness(p)}
    def evidence(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**final_release_evidence_bundle(p)}
    def create_manifest(self,actor_id,p):
        if p.get("actor_role") not in MANIFEST_ROLES: raise PermissionError("authorized human release engineer required")
        if not validate_upstream_certifications(p)["upstream_human_certifications_valid"]: raise ValueError("Release 107, 108 and 109 human certification provenance required")
        m=assess_release_manifest(p|{"expected_migration_head":"0105_final_production_go_live"})
        if not m["release_manifest_integrity_passed"]: raise ValueError("release manifest integrity gate failed")
        if not p.get("evidence_refs"): raise ValueError("release manifest must be evidence-bound")
        return self._immutable({"final_release_manifest_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_created":True,"created_by":actor_id,"created_at":self._now(),**p})
    def approve_go_live(self,actor_id,p):
        if p.get("actor_role") not in GO_LIVE_ROLES: raise PermissionError("authorized human go-live approver required")
        for k in ("final_release_manifest_version_id","release107_release_candidate_decision_version_id","release108_release_security_certification_version_id","release109_operational_readiness_certification_version_id"):
            if not p.get(k): raise ValueError(f"{k} is required")
        r=final_go_live_readiness(p)
        if p.get("decision")=="approve" and not r["final_go_live_ready"]: raise ValueError("all deterministic final go-live gates must pass")
        return self._immutable({"go_live_approval_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"approved_by":actor_id,"approved_at":self._now(),"automated_production_promotion":False,"readiness":r,**p})
    def record_deployment_verification(self,actor_id,p):
        if p.get("actor_role") not in DEPLOY_ROLES: raise PermissionError("authorized human deployment operator required")
        if not p.get("go_live_approval_version_id") or not p.get("final_release_manifest_version_id"): raise ValueError("human go-live approval and release manifest required")
        v=p.get("verification",{});
        if not v.get("post_deployment_verification_passed") or not p.get("evidence_refs"): raise ValueError("deployment verification must pass and be evidence-bound")
        return self._immutable({"deployment_verification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_executed":True,"verified_by":actor_id,"verified_at":self._now(),"automatic_promotion":False,**p})
    def certify_final_release(self,actor_id,p):
        if p.get("actor_role") not in FINAL_CERT_ROLES: raise PermissionError("authorized human final release certifier required")
        for k in ("release107_release_candidate_decision_version_id","release108_release_security_certification_version_id","release109_operational_readiness_certification_version_id","final_release_manifest_version_id","go_live_approval_version_id","deployment_verification_version_id"):
            if not p.get(k): raise ValueError(f"{k} is required")
        if not p.get("evidence_refs"): raise ValueError("final certification must be evidence-bound")
        return self._immutable({"final_release_certification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"certified_by":actor_id,"certified_at":self._now(),"automated_certification":False,**p})
    def create_hypercare_checkpoint(self,actor_id,p):
        if p.get("actor_role") not in HYPERCARE_ROLES: raise PermissionError("authorized human hypercare operator required")
        if not p.get("final_release_certification_version_id") or not p.get("evidence_refs"): raise ValueError("final certification and hypercare evidence required")
        return self._immutable({"hypercare_checkpoint_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_recorded":True,"recorded_by":actor_id,"recorded_at":self._now(),"assessment":assess_hypercare(p),**p})
    def close_hypercare(self,actor_id,p):
        if p.get("actor_role") not in HYPERCARE_CLOSE_ROLES: raise PermissionError("authorized human hypercare certifier required")
        if not p.get("final_release_certification_version_id") or not p.get("evidence_refs"): raise ValueError("final certification and evidence required")
        a=assess_hypercare(p)
        if p.get("decision")=="close" and (not a["command_center_ready"] or not a["slo_window_passed"] or a["open_sev1"]): raise ValueError("hypercare closure gates not satisfied")
        return self._immutable({"hypercare_closure_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"closed_by":actor_id,"closed_at":self._now(),"automated_closure":False,"assessment":a,**p})
