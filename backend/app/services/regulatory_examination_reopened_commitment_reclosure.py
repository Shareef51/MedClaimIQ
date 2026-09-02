from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reopened_commitment_reclosure import compare_recurrence_root_causes, reclosure_readiness, second_recurrence_assessment, sustainability_reset_window, version_hash

RECERTIFY_ROLES={"executive_certifier","regulatory_affairs","internal_auditor"}
RECLOSE_ROLES={"executive_certifier","regulatory_affairs"}
INDEPENDENT_ROLES={"independent_validator","internal_auditor"}

class RegulatoryExaminationReopenedCommitmentReclosureService:
    def __init__(self, db, tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, body:dict): body["version_hash"]=version_hash(body); return body
    def create_renewed_plan(self, actor_id:str, payload:dict):
        return self._immutable({"plan_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"draft","human_approval_required":True,"created_by":actor_id,"created_at":self._now(),**payload})
    def create_milestone(self, actor_id:str, payload:dict):
        return self._immutable({"milestone_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"open","created_by":actor_id,"created_at":self._now(),**payload})
    def compare_root_causes(self, payload:dict):
        return {"tenant_id":self.tenant_id,"recommendation_only":True,**compare_recurrence_root_causes(payload.get("prior",{}),payload.get("current",{}))}
    def recommend_control_redesign(self, actor_id:str, payload:dict):
        return self._immutable({"recommendation_id":str(uuid4()),"tenant_id":self.tenant_id,"recommendation_only":True,"human_control_change_approval_required":True,"created_by":actor_id,"created_at":self._now(),**payload})
    def independent_retest(self, actor_id:str, payload:dict):
        if payload.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human retest required")
        if payload.get("result") not in {"effective","partially_effective","ineffective","insufficient_evidence"}: raise ValueError("invalid retest result")
        return self._immutable({"retest_id":str(uuid4()),"tenant_id":self.tenant_id,"independent":True,"human_retest":True,"reviewed_by":actor_id,"reviewed_at":self._now(),**payload})
    def assess_readiness(self, payload:dict): return {"tenant_id":self.tenant_id,**reclosure_readiness(payload)}
    def assess_second_recurrence(self, payload:dict): return {"tenant_id":self.tenant_id,**second_recurrence_assessment(payload.get("history",[])),"recommendation_only":True}
    def define_sustainability_reset(self, payload:dict): return {"tenant_id":self.tenant_id,**sustainability_reset_window(payload)}
    def recertify(self, actor_id:str, commitment_id:str, payload:dict):
        if payload.get("reviewer_role") not in RECERTIFY_ROLES: raise PermissionError("authorized human recertifier required")
        if payload.get("decision") not in {"recertify","reject","return_for_remediation"}: raise ValueError("invalid recertification decision")
        readiness=payload.get("readiness",{})
        if payload.get("decision")=="recertify" and not readiness.get("ready"): raise ValueError("reclosure readiness gates are not complete")
        body={"recertification_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_decision":True,"recertified":payload.get("decision")=="recertify","decided_by":actor_id,"decided_at":self._now(),**payload}
        return self._immutable(body)
    def decide_reclosure(self, actor_id:str, commitment_id:str, payload:dict):
        if payload.get("reviewer_role") not in RECLOSE_ROLES: raise PermissionError("authorized human reclosure reviewer required")
        if payload.get("decision") not in {"reclose","reject","continue_monitoring"}: raise ValueError("invalid reclosure decision")
        if payload.get("decision")=="reclose" and not payload.get("recertification_id"): raise ValueError("human recertification required before reclosure")
        window=payload.get("sustainability_window",{})
        if payload.get("decision")=="reclose" and window.get("reset_required") is not True: raise ValueError("sustainability reset window required")
        body={"reclosure_version_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_decision":True,"reclosed":payload.get("decision")=="reclose","decided_by":actor_id,"decided_at":self._now(),**payload}
        return self._immutable(body)
