from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_post_intervention_surveillance import systemic_recurrence_signal, examination_match, cross_entity_propagation, reopening_readiness, version_hash

INDEPENDENT_ROLES={"internal_auditor","independent_validator"}
REOPEN_ROLES={"executive_certifier","chief_risk_officer","chief_compliance_officer"}

class RegulatoryExaminationPostInterventionSurveillanceService:
    def __init__(self, db, tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def surveillance_signal(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**systemic_recurrence_signal(payload)}
    def correlate_examination(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**examination_match(payload)}
    def open_investigation(self,actor_id:str,payload:dict):
        propagation=cross_entity_propagation(payload)
        return self._immutable({"recurrence_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"automated_reopen":False,"propagation":propagation,**payload})
    def independent_reassessment(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human reassessment required")
        return self._immutable({"independent_reassessment_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_assessment":True,"automated_certification":False,"created_by":actor_id,"created_at":self._now(),**payload})
    def reopening_readiness(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**reopening_readiness(payload)}
    def reopening_decision(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in REOPEN_ROLES: raise PermissionError("authorized human program reopening approver required")
        if payload.get("decision") not in {"reopen","reject","continue_surveillance"}: raise ValueError("invalid reopening decision")
        if payload.get("decision")=="reopen":
            if float(payload.get("reopening_readiness_score",0))<100: raise ValueError("reopening readiness must be 100")
            if not payload.get("investigation_version_id") or not payload.get("independent_reassessment_version_id"): raise ValueError("investigation and independent reassessment required")
        return self._immutable({"program_reopening_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
