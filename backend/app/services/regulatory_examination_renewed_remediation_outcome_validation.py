from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_renewed_remediation_outcome_validation import version_hash, outcome_measurement, reclosure_readiness, sustainability_status

EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}

class RegulatoryExaminationRenewedRemediationOutcomeValidationService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def measure_outcome(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**outcome_measurement(payload)}
    def independent_validate(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human recovery validator required")
        return self._immutable({"independent_recovery_validation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_validation":True,"automated_certification":False,"validated_by":actor_id,"validated_at":self._now(),**payload})
    def accept_residual_risk(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human required")
        return self._immutable({"residual_risk_acceptance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_acceptance":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def observe_sustainability(self,actor_id:str,payload:dict):
        return self._immutable({"sustainability_observation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),**payload})
    def sustainability(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**sustainability_status(payload)}
    def readiness(self,payload:dict): return {"tenant_id":self.tenant_id,**reclosure_readiness(payload)}
    def certify_recovery(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human required")
        if payload.get("decision") == "certify":
            r=reclosure_readiness(payload.get("readiness",{}))
            if not r["ready_for_human_executive_reclosure"]: raise ValueError("reclosure readiness gates are incomplete")
        return self._immutable({"executive_recovery_certification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_certification":True,"automated_certification":False,"certified_by":actor_id,"certified_at":self._now(),**payload})
    def reclose(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human required")
        if payload.get("decision") == "reclose":
            r=reclosure_readiness(payload.get("readiness",{}))
            if not r["ready_for_human_executive_reclosure"]: raise ValueError("reclosure readiness gates are incomplete")
        return self._immutable({"reclosure_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reclosure":True,"automated_reclosure":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
