from __future__ import annotations
from datetime import datetime,timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reauthorized_recovery_execution import *
EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}
EXECUTION_ROLES=EXECUTIVE_ROLES|INDEPENDENT_ROLES|{"recovery_governance","remediation_governance","regulatory_affairs","control_owner"}
class RegulatoryExaminationReauthorizedRecoveryExecutionService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p:dict): p["version_hash"]=version_hash(p); return p
    def create_program(self,actor_id:str,p:dict):
        if p.get("actor_role") not in EXECUTION_ROLES: raise PermissionError("authorized human recovery-governance role required")
        if not p.get("remediation_reauthorization_version_id"): raise ValueError("human remediation reauthorization version is required")
        return self._immutable({"reauthorized_recovery_execution_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reauthorization_reference_required":True,"automated_program_approval":False,"created_by":actor_id,"created_at":self._now(),**p})
    def rerehabilitation(self,p:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**control_rerehabilitation_status(p)}
    def deployment_sequence(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**deployment_sequence_assessment(p)}
    def critical_path(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**critical_path_assessment(p)}
    def detect_drift(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**implementation_drift(p)}
    def kpis(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**recovery_kpi_assessment(p)}
    def independent_assurance(self,actor_id:str,p:dict):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human reviewer required")
        result=independent_recovery_assurance(p)
        return self._immutable({"independent_recovery_assurance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reviewer":True,"automated_certification":False,"reviewed_by":actor_id,"reviewed_at":self._now(),"evaluation":result,**p})
    def readiness(self,p:dict): return {"tenant_id":self.tenant_id,**execution_readiness(p)}
    def executive_review(self,actor_id:str,p:dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human review required")
        if p.get("decision") not in {"continue","escalate","pause","request_more_evidence"}: raise ValueError("invalid executive progress decision")
        return self._immutable({"reauthorized_executive_progress_review_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**p})
