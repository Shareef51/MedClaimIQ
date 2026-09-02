from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_post_commitment_surveillance import sustainability_decay, match_new_examination, cross_entity_recurrence, compare_prior_certification, version_hash

REOPEN_ROLES={"regulatory_affairs","compliance_reviewer","internal_auditor","executive_certifier"}
INDEPENDENT_ROLES={"independent_validator","internal_auditor"}

class RegulatoryExaminationPostCommitmentSurveillanceService:
    def __init__(self, db, tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def record_observation(self, actor_id:str, payload:dict):
        body={"observation_id":str(uuid4()),"tenant_id":self.tenant_id,"recorded_by":actor_id,"recorded_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def evaluate_decay(self, payload:dict):
        return {"assessment_id":str(uuid4()),"tenant_id":self.tenant_id,"recommendation_only":True,"human_reopen_decision_required":True,**sustainability_decay(payload.get("observations",[]),payload.get("warning_threshold",80.0),payload.get("critical_threshold",60.0))}
    def match_examination(self, payload:dict):
        return {"tenant_id":self.tenant_id,"matches":match_new_examination(payload.get("closed_commitment",{}),payload.get("findings",[])),"recommendation_only":True}
    def propagate_cross_entity(self, payload:dict):
        return {"tenant_id":self.tenant_id,**cross_entity_recurrence(payload.get("signals",[]),payload.get("minimum_entities",2)),"recommendation_only":True}
    def compare_certification(self, payload:dict):
        return {"tenant_id":self.tenant_id,**compare_prior_certification(payload.get("certification",{}),payload.get("current_evidence",{})),"recommendation_only":True}
    def open_investigation(self, actor_id:str, payload:dict):
        body={"investigation_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"open","opened_by":actor_id,"opened_at":self._now(),"human_reopen_decision_required":True,**payload}; body["version_hash"]=version_hash(body); return body
    def link_renewed_action_plan(self, actor_id:str, payload:dict):
        body={"link_id":str(uuid4()),"tenant_id":self.tenant_id,"linked_by":actor_id,"linked_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def record_independent_reassessment(self, actor_id:str, payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human reassessment required")
        if payload.get("result") not in {"effective","partially_effective","ineffective","insufficient_evidence"}: raise ValueError("invalid reassessment result")
        body={"reassessment_id":str(uuid4()),"tenant_id":self.tenant_id,"independent":True,"human_reassessment":True,"reviewed_by":actor_id,"reviewed_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def decide_reopen(self, actor_id:str, commitment_id:str, payload:dict):
        if payload.get("reviewer_role") not in REOPEN_ROLES: raise PermissionError("authorized human reopen reviewer required")
        if payload.get("decision") not in {"reopen","dismiss","continue_monitoring"}: raise ValueError("invalid reopen decision")
        body={"reopen_version_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_decision":True,"reopened":payload.get("decision")=="reopen","decided_by":actor_id,"decided_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
