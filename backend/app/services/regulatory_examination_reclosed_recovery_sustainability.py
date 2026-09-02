from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosed_recovery_sustainability import recovery_decay_score,multi_cycle_recurrence,risk_rebound_correlation,reclosure_comparison,regulator_followup_correlation,enterprise_materiality,version_hash
INVESTIGATION_ROLES={"internal_auditor","chief_audit_executive","independent_assurance","regulatory_affairs","compliance_reviewer"}
ESCALATION_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier","chief_audit_executive"}
class RegulatoryExaminationReclosedRecoverySustainabilityService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload): payload["version_hash"]=version_hash(payload); return payload
    def decay(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**recovery_decay_score(p)}
    def recurrence(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**multi_cycle_recurrence(p)}
    def rebound(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**risk_rebound_correlation(p)}
    def compare(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**reclosure_comparison(p)}
    def regulator(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_followup_correlation(p)}
    def materiality(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**enterprise_materiality(p)}
    def open_investigation(self,actor_id,p):
        if p.get("actor_role") not in INVESTIGATION_ROLES: raise PermissionError("independent human supervisory investigator required")
        if not p.get("recurrence_evidence_refs"): raise ValueError("recurrence evidence references required")
        return self._immutable({"supervisory_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_opened":True,"automated_investigation_opening":False,"opened_by":actor_id,"opened_at":self._now(),**p})
    def escalate(self,actor_id,p):
        if p.get("actor_role") not in ESCALATION_ROLES: raise PermissionError("authorized executive/internal-audit human escalation decision required")
        if not p.get("investigation_version_id"): raise ValueError("human investigation reference required")
        if p.get("decision") not in {"escalate","continue_investigation","request_more_evidence","deescalate"}: raise ValueError("invalid supervisory escalation decision")
        return self._immutable({"supervisory_escalation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_program_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**p})
