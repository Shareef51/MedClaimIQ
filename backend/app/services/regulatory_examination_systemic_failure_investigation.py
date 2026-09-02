from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_systemic_failure_investigation import version_hash, reconstruct_multi_cycle_evidence, validate_prior_assumptions, reassess_root_causes, analyze_failed_control_redesign, map_cross_entity_causality, regulator_follow_up_impact, remediation_reauthorization_readiness

EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}
INVESTIGATOR_ROLES=EXECUTIVE_ROLES|INDEPENDENT_ROLES|{"regulatory_affairs","remediation_governance"}

class RegulatoryExaminationSystemicFailureInvestigationService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,payload:dict): payload["version_hash"]=version_hash(payload); return payload
    def create_investigation(self,actor_id:str,payload:dict):
        return self._immutable({"systemic_failure_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_conclusion_required":True,"automated_authorization":False,**payload})
    def reconstruct_evidence(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**reconstruct_multi_cycle_evidence(payload)}
    def validate_assumptions(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**validate_prior_assumptions(payload)}
    def reassess_root_cause(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**reassess_root_causes(payload)}
    def analyze_control_redesign(self,payload:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**analyze_failed_control_redesign(payload)}
    def causal_map(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**map_cross_entity_causality(payload)}
    def regulator_impact(self,payload:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_follow_up_impact(payload)}
    def create_strategy_candidate(self,actor_id:str,payload:dict):
        return self._immutable({"renewed_strategy_candidate_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"recommendation_only":True,"human_authorization_required":True,**payload})
    def independent_challenge(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human challenge required")
        if payload.get("decision") not in {"agree","challenge","request_more_evidence","escalate"}: raise ValueError("invalid independent challenge decision")
        return self._immutable({"independent_challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def readiness(self,payload:dict): return {"tenant_id":self.tenant_id,**remediation_reauthorization_readiness(payload)}
    def authorize_remediation(self,actor_id:str,payload:dict):
        if payload.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human approval required")
        if payload.get("decision") not in {"authorize","reject","defer"}: raise ValueError("invalid reauthorization decision")
        ready=remediation_reauthorization_readiness(payload.get("readiness",{}))
        if payload.get("decision")=="authorize" and not ready["ready_for_human_authorization"]: raise ValueError("reauthorization readiness gates are incomplete")
        return self._immutable({"remediation_reauthorization_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_authorization":True,"automated_authorization":False,"authorized_by":actor_id,"authorized_at":self._now(),"readiness_result":ready,**payload})
    def conclude_investigation(self,actor_id:str,payload:dict):
        if payload.get("investigator_role") not in INVESTIGATOR_ROLES: raise PermissionError("authorized human investigator required")
        return self._immutable({"investigation_conclusion_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_conclusion":True,"automated_conclusion":False,"concluded_by":actor_id,"concluded_at":self._now(),**payload})
