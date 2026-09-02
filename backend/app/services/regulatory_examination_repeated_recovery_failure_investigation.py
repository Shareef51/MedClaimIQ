from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_repeated_recovery_failure_investigation import version_hash,reconstruct_recovery_cycles,validate_recovery_assumptions,reassess_recovery_root_causes,analyze_failed_rehabilitation,map_recovery_causality,regulator_recovery_impact,remediation_reauthorization_readiness
EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}
INVESTIGATOR_ROLES=EXECUTIVE_ROLES|INDEPENDENT_ROLES|{"regulatory_affairs","remediation_governance"}
class RegulatoryExaminationRepeatedRecoveryFailureInvestigationService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p): p["version_hash"]=version_hash(p); return p
    def create_investigation(self,actor_id,p): return self._immutable({"repeated_recovery_failure_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"human_conclusion_required":True,"automated_authorization":False,**p})
    def reconstruct_evidence(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**reconstruct_recovery_cycles(p)}
    def validate_assumptions(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**validate_recovery_assumptions(p)}
    def reassess_root_cause(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**reassess_recovery_root_causes(p)}
    def analyze_rehabilitation(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**analyze_failed_rehabilitation(p)}
    def causal_map(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**map_recovery_causality(p)}
    def regulator_impact(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_recovery_impact(p)}
    def create_strategy_candidate(self,actor_id,p): return self._immutable({"renewed_recovery_strategy_candidate_version_id":str(uuid4()),"tenant_id":self.tenant_id,"created_by":actor_id,"created_at":self._now(),"recommendation_only":True,"human_authorization_required":True,**p})
    def independent_challenge(self,actor_id,p):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent internal-audit human challenge required")
        if p.get("decision") not in {"agree","challenge","request_more_evidence","escalate"}: raise ValueError("invalid independent challenge decision")
        return self._immutable({"recovery_independent_challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**p})
    def readiness(self,p): return {"tenant_id":self.tenant_id,**remediation_reauthorization_readiness(p)}
    def authorize_remediation(self,actor_id,p):
        if p.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human approval required")
        if p.get("decision") not in {"authorize","reject","defer"}: raise ValueError("invalid remediation reauthorization decision")
        ready=remediation_reauthorization_readiness(p.get("readiness",{}))
        if p.get("decision")=="authorize" and not ready["ready_for_human_authorization"]: raise ValueError("recovery remediation reauthorization gates are incomplete")
        return self._immutable({"recovery_remediation_reauthorization_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_authorization":True,"automated_authorization":False,"authorized_by":actor_id,"authorized_at":self._now(),"readiness_result":ready,**p})
    def conclude_investigation(self,actor_id,p):
        if p.get("investigator_role") not in INVESTIGATOR_ROLES: raise PermissionError("authorized human recovery investigator required")
        return self._immutable({"recovery_investigation_conclusion_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_conclusion":True,"automated_conclusion":False,"concluded_by":actor_id,"concluded_at":self._now(),**p})
