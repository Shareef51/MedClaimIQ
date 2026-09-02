from __future__ import annotations
from datetime import datetime,timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reopened_recovery_investigation import *
EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance"}
INVESTIGATOR_ROLES=EXECUTIVE_ROLES|INDEPENDENT_ROLES|{"regulatory_affairs","remediation_governance","recovery_governance"}
class RegulatoryExaminationReopenedRecoveryInvestigationService:
 def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
 def _now(self): return datetime.now(timezone.utc).isoformat()
 def _immutable(self,p:dict): p["version_hash"]=version_hash(p); return p
 def create_investigation(self,actor_id:str,p:dict):
  if p.get("actor_role") not in INVESTIGATOR_ROLES: raise PermissionError("authorized human investigator required")
  return self._immutable({"reopened_recovery_investigation_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_investigation":True,"automated_authorization":False,"created_by":actor_id,"created_at":self._now(),**p})
 def reconstruct_decay(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**reconstruct_systemic_decay(p)}
 def validate_assumptions(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**validate_prior_recovery_assumptions(p)}
 def reassess_root_causes(self,p:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**reassess_decay_root_causes(p)}
 def analyze_control_gaps(self,p:dict): return {"tenant_id":self.tenant_id,"recommendation_only":True,**analyze_cross_entity_control_gaps(p)}
 def regulator_impact(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulator_follow_up_impact(p)}
 def align_commitments(self,p:dict): return {"tenant_id":self.tenant_id,"analysis_only":True,**commitment_alignment(p)}
 def create_strategy(self,actor_id:str,p:dict): return self._immutable({"renewed_recovery_strategy_version_id":str(uuid4()),"tenant_id":self.tenant_id,"recommendation_only":True,"human_authorization_required":True,"created_by":actor_id,"created_at":self._now(),**p})
 def independent_challenge(self,actor_id:str,p:dict):
  if p.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human challenge required")
  if p.get("decision") not in {"agree","challenge","request_more_evidence","escalate"}: raise ValueError("invalid independent challenge decision")
  return self._immutable({"recovery_independent_challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**p})
 def readiness(self,p:dict): return {"tenant_id":self.tenant_id,**authorization_readiness(p)}
 def authorize(self,actor_id:str,p:dict):
  if p.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human approval required")
  if p.get("decision") not in {"authorize","reject","defer"}: raise ValueError("invalid authorization decision")
  ready=authorization_readiness(p.get("readiness",{}))
  if p.get("decision")=="authorize" and not ready["ready_for_human_authorization"]: raise ValueError("authorization readiness gates are incomplete")
  return self._immutable({"renewed_remediation_authorization_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_authorization":True,"automated_authorization":False,"authorized_by":actor_id,"authorized_at":self._now(),"readiness_result":ready,**p})
