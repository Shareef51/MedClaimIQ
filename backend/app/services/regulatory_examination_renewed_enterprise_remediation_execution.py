from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_renewed_enterprise_remediation_execution import version_hash, critical_path_status, implementation_drift, effectiveness_kpis, recovery_assurance_readiness, residual_systemic_risk

EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}

class RegulatoryExaminationRenewedEnterpriseRemediationExecutionService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def create_program(self,actor_id:str,payload:dict):
        return self._immutable({"renewed_enterprise_program_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_authorized_strategy_required":True,"automated_program_approval":False,**payload})
    def create_workstream(self,actor_id:str,payload:dict):
        return self._immutable({"workstream_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),**payload})
    def create_control_transformation(self,actor_id:str,payload:dict):
        return self._immutable({"control_transformation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"recommendation_only":True,"human_approval_required":True,**payload})
    def critical_path(self,payload:dict): return {"tenant_id":self.tenant_id,**critical_path_status(payload)}
    def detect_drift(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**implementation_drift(payload)}
    def kpis(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**effectiveness_kpis(payload)}
    def independent_recovery_test(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human recovery tester required")
        return self._immutable({"independent_recovery_test_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_test_conclusion":True,"automated_certification":False,"tested_by":actor_id,"tested_at":self._now(),**payload})
    def readiness(self,payload:dict): return {"tenant_id":self.tenant_id,**recovery_assurance_readiness(payload)}
    def risk_reassessment(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**residual_systemic_risk(payload)}
    def decide_residual_risk(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human required")
        if payload.get("decision") == "accept":
            ready=recovery_assurance_readiness(payload.get("readiness",{}))
            if not ready["ready_for_human_residual_risk_reassessment"]: raise ValueError("recovery assurance gates are incomplete")
        return self._immutable({"residual_systemic_risk_decision_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_acceptance":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def executive_progress(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human governance required")
        return self._immutable({"executive_progress_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_governance":True,"automated_governance":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
