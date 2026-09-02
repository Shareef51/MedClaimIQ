from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosure_sustainability import sustainability_decay, repeat_recurrence_score, escalation_tier, compare_reclosures, version_hash

HUMAN_REVIEW_ROLES={"regulatory_affairs","executive_certifier","internal_auditor","compliance_reviewer","independent_validator"}
EXEC_AUDIT_ROLES={"executive_certifier","internal_auditor"}
class RegulatoryExaminationReclosureSustainabilityService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,b:dict): b["version_hash"]=version_hash(b); return b
    def record_observation(self,actor_id:str,payload:dict):
        assessment=sustainability_decay(payload)
        return self._immutable({"observation_id":str(uuid4()),"tenant_id":self.tenant_id,"monitoring_only":True,"created_by":actor_id,"created_at":self._now(),**payload,"assessment":assessment})
    def assess_recurrence(self,payload:dict):
        return {"tenant_id":self.tenant_id,"recommendation_only":True,**repeat_recurrence_score(payload.get("history",[]),payload.get("cross_entity_count",0))}
    def compare_reclosures(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**compare_reclosures(payload.get("prior",{}),payload.get("current",{}))}
    def create_escalation(self,actor_id:str,payload:dict):
        a=escalation_tier(payload)
        return self._immutable({"escalation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"open","human_closure_required":True,"created_by":actor_id,"created_at":self._now(),**payload,"assessment":a})
    def open_investigation(self,actor_id:str,payload:dict):
        role=payload.get("reviewer_role")
        if role not in HUMAN_REVIEW_ROLES: raise PermissionError("authorized human investigation reviewer required")
        return self._immutable({"investigation_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"status":"open","opened_by":actor_id,"opened_at":self._now(),**payload})
    def create_governance_action(self,actor_id:str,payload:dict):
        role=payload.get("reviewer_role"); action=payload.get("action_type")
        if role not in HUMAN_REVIEW_ROLES: raise PermissionError("authorized human governance reviewer required")
        if action in {"reopen_commitment","executive_escalation","internal_audit_review"} and role not in EXEC_AUDIT_ROLES|{"regulatory_affairs"}: raise PermissionError("elevated human authority required")
        return self._immutable({"governance_action_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"created_by":actor_id,"created_at":self._now(),**payload})
