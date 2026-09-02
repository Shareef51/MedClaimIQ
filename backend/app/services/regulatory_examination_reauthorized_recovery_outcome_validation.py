from __future__ import annotations
from datetime import datetime,timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reauthorized_recovery_outcome_validation import *
EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance","independent_validator"}

class RegulatoryExaminationReauthorizedRecoveryOutcomeValidationService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload): payload["version_hash"]=version_hash(payload); return payload
    def outcomes(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**reauthorized_recovery_outcomes(payload)}
    def risk_reduction(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**systemic_risk_reduction(payload)}
    def entity_completion(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**cross_entity_completion(payload)}
    def repeated_failure_effectiveness(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**repeated_failure_control_effectiveness(payload)}
    def commitment_completion(self,payload): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulatory_commitment_completion(payload)}
    def independent_validate(self,actor_id,payload):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human recovery outcome reviewer required")
        result=independent_recovery_outcome_assurance(payload)
        return self._immutable({"independent_outcome_validation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reviewer":True,"automated_certification":False,"reviewed_by":actor_id,"reviewed_at":self._now(),"evaluation":result,**payload})
    def sustainability(self,payload):
        return self._immutable({"sustainability_assessment_version_id":str(uuid4()),"tenant_id":self.tenant_id,"analysis_only":True,"automated_reclosure":False,"assessed_at":self._now(),"evaluation":sustainability_assessment(payload),**payload})
    def readiness(self,payload): return {"tenant_id":self.tenant_id,**reclosure_readiness(payload)}
    def residual_risk_reassessment(self,actor_id,payload):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human residual-risk decision required")
        if payload.get("decision") not in {"accept","reject","request_more_evidence"}: raise ValueError("invalid residual-risk reassessment decision")
        return self._immutable({"residual_risk_decision_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_risk_acceptance":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def recertify_recovery(self,actor_id,payload):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human recovery recertification required")
        if payload.get("decision") not in {"recertify","withhold","request_more_evidence"}: raise ValueError("invalid recovery recertification decision")
        req=["independent_outcome_validation_version_id","residual_risk_decision_version_id","sustainability_assessment_version_id"]
        if any(not payload.get(k) for k in req): raise ValueError("independent outcome validation, residual-risk decision and sustainability assessment references are required")
        return self._immutable({"recovery_recertification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_recertification":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def reclose_program(self,actor_id,payload):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human program reclosure required")
        if payload.get("decision") not in {"reclose","withhold","request_more_evidence"}: raise ValueError("invalid sustainability reclosure decision")
        if not payload.get("recovery_recertification_version_id"): raise ValueError("human recovery recertification reference is required")
        return self._immutable({"sustainability_reclosure_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_reclosure":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
