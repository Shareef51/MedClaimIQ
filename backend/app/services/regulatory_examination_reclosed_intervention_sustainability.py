from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosed_intervention_sustainability import version_hash, sustainability_health, multi_cycle_recurrence, prior_reclosure_comparison, cross_entity_propagation, regulator_follow_up_correlation, enterprise_materiality

EXECUTIVE_ROLES={"executive_certifier","chief_risk_officer","chief_compliance_officer","executive_risk_committee"}
AUDIT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}
GOVERNANCE_ROLES=EXECUTIVE_ROLES|AUDIT_ROLES|{"regulatory_affairs","remediation_governance"}

class RegulatoryExaminationReclosedInterventionSustainabilityService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def observe_sustainability(self,actor_id:str,payload:dict):
        result=sustainability_health(payload)
        return self._immutable({"surveillance_observation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"monitoring_only":True,"automated_reopening":False,**payload,**result})
    def score_multi_cycle_recurrence(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**multi_cycle_recurrence(payload)}
    def compare_reclosures(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**prior_reclosure_comparison(payload.get("prior",{}),payload.get("current",{}))}
    def propagation(self,payload:dict): return {"tenant_id":self.tenant_id,"monitoring_only":True,**cross_entity_propagation(payload)}
    def correlate_regulator_follow_up(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_follow_up_correlation(payload)}
    def materiality(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**enterprise_materiality(payload)}
    def create_escalation(self,actor_id:str,payload:dict):
        if payload.get("escalation_tier") in {"high","critical"}:
            payload["executive_review_required"]=True; payload["internal_audit_review_required"]=True
        return self._immutable({"supervisory_escalation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_review_required":True,"automated_governance_action":False,**payload})
    def create_investigation(self,actor_id:str,payload:dict):
        return self._immutable({"supervisory_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_investigation":True,"automated_conclusion":False,**payload})
    def human_challenge(self,actor_id:str,payload:dict):
        role=payload.get("reviewer_role")
        if role not in EXECUTIVE_ROLES|AUDIT_ROLES: raise PermissionError("executive or internal-audit human challenge required")
        if payload.get("decision") not in {"agree","challenge","escalate","request_more_evidence"}: raise ValueError("invalid challenge decision")
        return self._immutable({"human_challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def governance_action(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in GOVERNANCE_ROLES: raise PermissionError("authorized human governance role required")
        if payload.get("action_type") in {"reopen_program","reclose_program","accept_residual_systemic_risk","certify_effectiveness"}: raise PermissionError("Release 78 does not delegate reopen/reclose/risk-acceptance/certification authority")
        if payload.get("decision") not in {"approve_investigation","commission_reassessment","create_remediation_candidate","defer","reject"}: raise ValueError("invalid governance decision")
        return self._immutable({"renewed_governance_action_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_program_reopening":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
