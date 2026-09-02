from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosed_recovery_surveillance import version_hash, surveillance_score, reopening_readiness, examination_match_score

EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}

class RegulatoryExaminationReclosedRecoverySurveillanceService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def assess_surveillance(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**surveillance_score(payload)}
    def match_examination(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**examination_match_score(payload)}
    def create_investigation(self,actor_id:str,payload:dict):
        if payload.get("actor_role") in {"ai_agent","worker","system"}: raise PermissionError("human investigator required")
        return self._immutable({"sustainability_breach_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_investigation":True,"created_by":actor_id,"created_at":self._now(),**payload})
    def independent_reassess(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human reassessor required")
        return self._immutable({"independent_reassessment_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reassessment":True,"automated_reassessment":False,"reassessed_by":actor_id,"reassessed_at":self._now(),**payload})
    def readiness(self,payload:dict): return {"tenant_id":self.tenant_id,**reopening_readiness(payload)}
    def decide_reopening(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human required")
        if payload.get("decision") == "reopen":
            r=reopening_readiness(payload.get("readiness",{}))
            if not r["ready_for_human_enterprise_reopening"]: raise ValueError("enterprise reopening gates are incomplete")
        return self._immutable({"enterprise_reopening_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reopening":True,"automated_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
