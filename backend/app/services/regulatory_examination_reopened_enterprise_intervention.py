from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reopened_enterprise_intervention import version_hash, root_cause_comparison, propagation_readiness, second_systemic_recurrence, reclosure_readiness

INDEPENDENT_ROLES={"internal_auditor","independent_validator","independent_assurance"}
RISK_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee"}
EXECUTIVE_ROLES={"executive_certifier","chief_risk_officer","chief_compliance_officer"}

class RegulatoryExaminationReopenedEnterpriseInterventionService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def create_plan(self,actor_id:str,payload:dict):
        return self._immutable({"reopened_intervention_plan_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_approval_required":True,"automated_program_approval":False,**payload})
    def create_action(self,actor_id:str,payload:dict):
        return self._immutable({"renewed_systemic_action_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"automated_completion_certification":False,**payload})
    def compare_root_causes(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**root_cause_comparison(payload.get("prior",{}),payload.get("current",{}))}
    def propagation_readiness(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**propagation_readiness(payload)}
    def control_redesign_recommendation(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,"human_approval_required":True,"automated_control_change":False,**payload}
    def independent_revalidation(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human revalidation required")
        if payload.get("result") not in {"pass","fail","partial"}: raise ValueError("invalid revalidation result")
        return self._immutable({"independent_revalidation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_assessment":True,"automated_certification":False,"created_by":actor_id,"created_at":self._now(),**payload})
    def second_recurrence(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**second_systemic_recurrence(payload.get("history",[]))}
    def sustainability_reset(self,payload:dict):
        severity=str(payload.get("severity","high")).lower(); days=payload.get("minimum_days") or {"low":90,"moderate":120,"high":180,"critical":365}.get(severity,180)
        if int(payload.get("recurrence_count",1))>=2: days=max(int(days),365)
        return {"tenant_id":self.tenant_id,"minimum_monitoring_days":int(days),"reset_required":True,"human_validation_required":True,"automatic_reclosure_allowed":False}
    def residual_risk_reassessment(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in RISK_ROLES: raise PermissionError("authorized human residual systemic risk reassessment required")
        if payload.get("decision") not in {"accept","reject","escalate"}: raise ValueError("invalid residual risk decision")
        return self._immutable({"residual_risk_reassessment_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_risk_acceptance":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def reclosure_readiness(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**reclosure_readiness(payload)}
    def executive_recertification(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized human executive recertifier required")
        if payload.get("decision") not in {"certify","reject","defer"}: raise ValueError("invalid recertification decision")
        if payload.get("decision")=="certify" and int(payload.get("readiness_score",0))<100: raise ValueError("reclosure readiness must be 100")
        return self._immutable({"executive_recertification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_certification":True,"automated_certification":False,"certified_by":actor_id,"certified_at":self._now(),**payload})
    def reclose_program(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized human program reclosure approver required")
        if payload.get("decision") not in {"reclose","reject","continue_remediation"}: raise ValueError("invalid reclosure decision")
        if payload.get("decision")=="reclose" and not payload.get("executive_recertification_id"): raise ValueError("executive recertification required")
        return self._immutable({"program_reclosure_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_reclosure":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
