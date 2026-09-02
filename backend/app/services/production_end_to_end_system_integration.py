from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.production_end_to_end_system_integration import *

RELEASE_ENGINEER_ROLES={"release_engineer","platform_engineer","site_reliability_engineer","quality_engineer","tenant_admin"}
RELEASE_DECISION_ROLES={"release_manager","head_of_engineering","chief_technology_officer","change_advisory_board","tenant_admin"}

class ProductionEndToEndSystemIntegrationService:
    def __init__(self, db, tenant_id: str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload: dict):
        result=dict(payload); result["version_hash"]=version_hash(result); result["immutable"]=True; return result
    def golden_journey(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_golden_journey(payload)}
    def api_contracts(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_api_contract_regression(payload)}
    def tenant_isolation(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_tenant_isolation(payload)}
    def workflow_recovery(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_workflow_recovery(payload)}
    def event_sse(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_event_sse_integrity(payload)}
    def failure_injection(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_failure_injection(payload)}
    def migration_chain(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_migration_chain(payload)}
    def readiness(self,payload): return {"tenant_id":self.tenant_id,"recommendation_only":True,**release_candidate_readiness(payload)}
    def report(self,payload): return {"tenant_id":self.tenant_id,"recommendation_only":True,**consolidated_readiness_report(payload)}
    def create_integration_run(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in RELEASE_ENGINEER_ROLES: raise PermissionError("authorized human release/integration engineer required")
        if not payload.get("release_manifest_ref") or not payload.get("evidence_refs"): raise ValueError("release manifest and evidence references are required")
        readiness=release_candidate_readiness({"gates":payload.get("gate_results",{}),"quality_scores":payload.get("quality_scores",{}),"evidence_refs":payload.get("evidence_refs",[]),"release_manifest_ref":payload.get("release_manifest_ref")})
        return self._immutable({"integration_run_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_initiated":True,"automated_candidate_declaration":False,"executed_by":actor_id,"executed_at":self._now(),"readiness":readiness,**payload})
    def decide_candidate(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in RELEASE_DECISION_ROLES: raise PermissionError("authorized human release-candidate decision maker required")
        if not payload.get("integration_run_version_id"): raise ValueError("immutable integration run reference is required")
        if not payload.get("evidence_refs"): raise ValueError("evidence-bound release-candidate decision is required")
        readiness=payload.get("readiness",{})
        if payload.get("decision")=="declare_candidate" and not readiness.get("release_candidate_ready",False): raise ValueError("all deterministic release-candidate gates must pass before declaration")
        return self._immutable({"release_candidate_decision_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_production_promotion":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
