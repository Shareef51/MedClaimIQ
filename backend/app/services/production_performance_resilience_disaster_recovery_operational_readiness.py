from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.production_performance_resilience_disaster_recovery_operational_readiness import *

OPERATIONAL_TEST_ROLES={"site_reliability_engineer","platform_engineer","performance_engineer","disaster_recovery_engineer","release_engineer","tenant_admin"}
OPERATIONAL_CERTIFICATION_ROLES={"head_of_site_reliability","head_of_platform","operations_director","operational_readiness_certifier","chief_technology_officer","tenant_admin"}

class ProductionPerformanceResilienceDisasterRecoveryOperationalReadinessService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p): r=dict(p); r["version_hash"]=version_hash(r); r["immutable"]=True; return r
    def load(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_load_stress_soak(p)}
    def noisy_neighbor(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_noisy_neighbor(p)}
    def ai_slo(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_ai_rag_agent_slo_cost(p)}
    def dependency(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_dependency_resilience(p)}
    def provider(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_provider_outage_fallback(p)}
    def kubernetes(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_kubernetes_disruption(p)}
    def backup_restore(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_backup_restore(p)}
    def dr_objectives(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_dr_rpo_rto(p)}
    def failover(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_failover_failback(p)}
    def capacity(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_autoscaling_capacity(p)}
    def observability(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_observability_alert_runbooks(p)}
    def incident_response(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_incident_response_exercise(p)}
    def readiness(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**operational_go_live_readiness(p)}
    def evidence_pack(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**operational_evidence_pack(p)}
    def create_drill_run(self,actor_id,payload):
        if payload.get("actor_role") not in OPERATIONAL_TEST_ROLES: raise PermissionError("authorized human SRE/platform/performance/DR engineer required")
        if not payload.get("release107_release_candidate_decision_version_id"): raise ValueError("Release 107 human release-candidate decision reference is required")
        if not payload.get("release108_release_security_certification_version_id"): raise ValueError("Release 108 human release-security certification reference is required")
        if not payload.get("evidence_refs"): raise ValueError("operational drill run must be evidence-bound")
        readiness=operational_go_live_readiness(payload)
        return self._immutable({"operational_drill_run_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_initiated":True,"executed_by":actor_id,"executed_at":self._now(),"readiness":readiness,**payload})
    def certify(self,actor_id,payload):
        if payload.get("actor_role") not in OPERATIONAL_CERTIFICATION_ROLES: raise PermissionError("authorized human operational-readiness certifier required")
        for key in ("release107_release_candidate_decision_version_id","release108_release_security_certification_version_id","operational_drill_run_version_id"):
            if not payload.get(key): raise ValueError(f"{key} is required")
        if not payload.get("evidence_refs"): raise ValueError("operational certification must be evidence-bound")
        readiness=payload.get("readiness",{})
        if payload.get("decision")=="certify" and not readiness.get("operational_go_live_ready",False): raise ValueError("all deterministic operational go-live gates must pass before certification")
        return self._immutable({"operational_readiness_certification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"certified_by":actor_id,"certified_at":self._now(),"automated_production_promotion":False,**payload})
