from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosed_reauthorized_recovery_surveillance import *
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance","independent_validator"}
INVESTIGATION_ROLES={"internal_auditor","chief_audit_executive","independent_assurance","regulatory_affairs","compliance_reviewer"}
EXECUTIVE_CHALLENGE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","chief_audit_executive","executive_certifier"}
REOPEN_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}

class RegulatoryExaminationReclosedReauthorizedRecoverySurveillanceService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload): payload["version_hash"]=version_hash(payload); return payload
    def decay(self,p): return {"tenant_id":self.tenant_id,"monitoring_only":True,**repeated_recovery_decay(p)}
    def rebound(self,p): return {"tenant_id":self.tenant_id,"monitoring_only":True,**systemic_risk_rebound(p)}
    def recurrence(self,p): return {"tenant_id":self.tenant_id,"monitoring_only":True,**cross_entity_recurrence(p)}
    def compare(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**prior_reclosure_comparison(p)}
    def correlate_findings(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**examination_finding_correlation(p)}
    def regulator_followups(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_followup_linkage(p)}
    def create_investigation(self,actor_id,p):
        if p.get("actor_role") not in INVESTIGATION_ROLES: raise PermissionError("authorized independent/human supervisory investigator required")
        if not p.get("evidence_refs") or not p.get("surveillance_version_refs"): raise ValueError("surveillance and evidence references required")
        return self._immutable({"reauthorized_recovery_decay_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_investigation":True,"automated_investigation_opening":False,"opened_by":actor_id,"opened_at":self._now(),**p})
    def independent_reassess(self,actor_id,p):
        if p.get("actor_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human recovery reassessor required")
        if not p.get("investigation_version_id"): raise ValueError("human investigation reference required")
        return self._immutable({"independent_recovery_reassessment_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reassessment":True,"automated_reassessment":False,"reassessed_by":actor_id,"reassessed_at":self._now(),**p})
    def supervisory_challenge(self,actor_id,p):
        if p.get("actor_role") not in EXECUTIVE_CHALLENGE_ROLES: raise PermissionError("authorized executive/internal-audit human challenge required")
        if not p.get("investigation_version_id") or not p.get("independent_reassessment_version_id"): raise ValueError("investigation and independent reassessment references required")
        return self._immutable({"supervisory_recovery_challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**p})
    def readiness(self,p): return {"tenant_id":self.tenant_id,**enterprise_reopening_readiness(p)}
    def decide_reopening(self,actor_id,p):
        if p.get("actor_role") not in REOPEN_ROLES: raise PermissionError("authorized executive human enterprise reopening decision required")
        required=["investigation_version_id","independent_reassessment_version_id","supervisory_challenge_version_id"]
        if any(not p.get(k) for k in required): raise ValueError("investigation, independent reassessment and supervisory challenge references required")
        if p.get("decision") == "reopen":
            r=enterprise_reopening_readiness(p.get("readiness",{}))
            if not r["ready_for_human_enterprise_reopening"]: raise ValueError("enterprise reopening gates are incomplete")
        return self._immutable({"enterprise_reauthorized_recovery_reopening_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reopening":True,"automated_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**p})
