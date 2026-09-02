from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_enterprise_intervention_sustainability import systemic_risk_reduction, sustainability_assurance, intervention_closure_readiness, recurrence_reopen_signal, version_hash

INDEPENDENT_ROLES={"internal_auditor","independent_validator"}
RISK_ACCEPTANCE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_certifier"}
EXECUTIVE_CLOSURE_ROLES={"executive_certifier","chief_risk_officer","chief_compliance_officer"}

class RegulatoryExaminationEnterpriseInterventionSustainabilityService:
    def __init__(self, db, tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def risk_reduction(self,payload:dict): return {"tenant_id":self.tenant_id,**systemic_risk_reduction(payload)}
    def sustainability_assurance(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human sustainability reviewer required")
        assessment=sustainability_assurance(payload)
        return self._immutable({"sustainability_assurance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"independent_human_assurance":True,"automated_certification":False,"created_by":actor_id,"created_at":self._now(),"assessment":assessment,**payload})
    def accept_residual_risk(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in RISK_ACCEPTANCE_ROLES: raise PermissionError("authorized human residual-risk acceptor required")
        if payload.get("decision") not in {"accept","reject","return_for_remediation"}: raise ValueError("invalid residual risk decision")
        return self._immutable({"residual_risk_acceptance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_risk_acceptance":False,"accepted_by":actor_id,"accepted_at":self._now(),**payload})
    def closure_readiness(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**intervention_closure_readiness(payload)}
    def executive_closure(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in EXECUTIVE_CLOSURE_ROLES: raise PermissionError("authorized human executive closure certifier required")
        if payload.get("decision") not in {"close","reject","return_for_remediation"}: raise ValueError("invalid program closure decision")
        if payload.get("decision")=="close":
            if not payload.get("residual_risk_acceptance_version_id") or not payload.get("sustainability_assurance_version_id"): raise ValueError("risk acceptance and sustainability assurance required")
            if float(payload.get("closure_readiness_score",0)) < 100: raise ValueError("closure readiness must be 100 before closure")
        return self._immutable({"program_closure_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_closure":False,"closed_by":actor_id,"closed_at":self._now(),**payload})
    def recurrence_signal(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**recurrence_reopen_signal(payload)}
