from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_enterprise_intervention_execution import program_execution_readiness, resource_capacity_risk, effectiveness_assurance, dependency_concentration, version_hash

PROGRAM_PLANNER_ROLES={"chief_risk_officer","chief_compliance_officer","executive_certifier","regulatory_affairs"}
INDEPENDENT_ASSURANCE_ROLES={"internal_auditor","independent_validator"}
EXECUTIVE_CERTIFIER_ROLES={"executive_certifier","chief_risk_officer","chief_compliance_officer"}

class RegulatoryExaminationEnterpriseInterventionExecutionService:
    def __init__(self, db, tenant_id: str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, body: dict): body["version_hash"]=version_hash(body); return body
    def create_program(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in PROGRAM_PLANNER_ROLES: raise PermissionError("authorized human enterprise remediation planner required")
        return self._immutable({"intervention_program_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"approved_for_execution","human_program_authority":True,"automated_approval":False,"created_by":actor_id,"created_at":self._now(),**payload})
    def execution_readiness(self, payload: dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**program_execution_readiness(payload)}
    def checkpoint(self, actor_id: str, payload: dict):
        if not payload.get("evidence_refs") or not payload.get("evidence_hashes"): raise ValueError("evidence refs and hashes required")
        return self._immutable({"implementation_checkpoint_id":str(uuid4()),"tenant_id":self.tenant_id,"evidence_bound":True,"created_by":actor_id,"created_at":self._now(),**payload})
    def capacity_risk(self, payload: dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**resource_capacity_risk(payload)}
    def dependency_concentration(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**dependency_concentration(payload)}
    def independent_assurance(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ASSURANCE_ROLES: raise PermissionError("independent human assurance reviewer required")
        assessment=effectiveness_assurance(payload)
        return self._immutable({"independent_assurance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"independent_human_assurance":True,"certification_decision":False,"created_by":actor_id,"created_at":self._now(),"assessment":assessment,**payload})
    def executive_certification(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in EXECUTIVE_CERTIFIER_ROLES: raise PermissionError("authorized human executive certifier required")
        if payload.get("decision") not in {"certify","reject","return_for_remediation"}: raise ValueError("invalid executive certification decision")
        if payload.get("decision")=="certify" and not payload.get("independent_assurance_version_id"): raise ValueError("independent assurance required before certification")
        return self._immutable({"executive_certification_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_certification":False,"certified_by":actor_id,"certified_at":self._now(),**payload})
