from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.production_security_privacy_compliance_red_team import *

SECURITY_TEST_ROLES={"security_engineer","application_security_engineer","privacy_engineer","red_team_engineer","security_architect","tenant_admin"}
SECURITY_WAIVER_ROLES={"chief_information_security_officer","security_risk_officer","security_governance_lead","tenant_admin"}
SECURITY_CERTIFICATION_ROLES={"chief_information_security_officer","head_of_security","security_certifier","tenant_admin"}

class ProductionSecurityPrivacyComplianceRedTeamService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p): r=dict(p); r["version_hash"]=version_hash(r); r["immutable"]=True; return r
    def cross_tenant(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_cross_tenant_penetration(p)}
    def authorization(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_authorization_abuse(p)}
    def prompt_injection(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_prompt_injection(p)}
    def rag_abuse(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_rag_poisoning_exfiltration(p)}
    def mcp_abuse(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_mcp_tool_abuse(p)}
    def agent_boundary(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_agent_privilege_boundary(p)}
    def leakage(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_phi_pii_leakage(p)}
    def supply_chain(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_supply_chain(p)}
    def api_fuzzing(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_api_fuzzing(p)}
    def audit_tamper(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_audit_tamper(p)}
    def multimodal(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**assess_adversarial_multimodal(p)}
    def readiness(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**security_release_readiness(p)}
    def evidence_pack(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**compliance_evidence_pack(p)}
    def create_red_team_run(self,actor_id,payload):
        if payload.get("actor_role") not in SECURITY_TEST_ROLES: raise PermissionError("authorized human security/red-team engineer required")
        if not payload.get("release107_release_candidate_decision_version_id"): raise ValueError("Release 107 human release-candidate decision reference is required")
        if not payload.get("evidence_refs"): raise ValueError("evidence-bound security red-team run is required")
        readiness=security_release_readiness(payload)
        return self._immutable({"security_red_team_run_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_initiated":True,"executed_by":actor_id,"executed_at":self._now(),"readiness":readiness,**payload})
    def approve_waiver(self,actor_id,payload):
        if payload.get("actor_role") not in SECURITY_WAIVER_ROLES: raise PermissionError("authorized human security-risk waiver approver required")
        eligibility=validate_waiver_eligibility(payload)
        if not eligibility["waiver_eligible"]: raise ValueError("critical/high or non-waivable security findings cannot be waived; compensating controls, expiry and evidence are required")
        return self._immutable({"security_waiver_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_approved":True,"approved_by":actor_id,"approved_at":self._now(),"approved":True,"eligibility":eligibility,**payload})
    def certify(self,actor_id,payload):
        if payload.get("actor_role") not in SECURITY_CERTIFICATION_ROLES: raise PermissionError("authorized human release-security certifier required")
        if not payload.get("release107_release_candidate_decision_version_id") or not payload.get("security_red_team_run_version_id"): raise ValueError("Release 107 human release-candidate and immutable red-team run references are required")
        if not payload.get("evidence_refs"): raise ValueError("security certification must be evidence-bound")
        readiness=payload.get("readiness",{})
        if payload.get("decision")=="certify" and not readiness.get("release_security_ready",False): raise ValueError("all deterministic release-security gates must pass before certification")
        return self._immutable({"release_security_certification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"certified_by":actor_id,"certified_at":self._now(),"automated_production_promotion":False,**payload})
