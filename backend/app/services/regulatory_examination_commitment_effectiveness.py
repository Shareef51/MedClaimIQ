from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_commitment_effectiveness import closure_readiness, sustainability_state, recurrence_match, version_hash

CLOSURE_CERTIFIER_ROLES={"regulatory_affairs","compliance_reviewer","legal_reviewer","executive_certifier"}
REOPEN_REVIEW_ROLES={"regulatory_affairs","compliance_reviewer","internal_auditor","executive_certifier"}
INDEPENDENT_VALIDATOR_ROLES={"independent_validator","internal_auditor"}

class RegulatoryExaminationCommitmentEffectivenessService:
    def __init__(self, db, tenant_id: str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def create_validation(self, actor_id: str, payload: dict):
        if payload.get("validator_role") not in INDEPENDENT_VALIDATOR_ROLES: raise PermissionError("independent human validator required")
        if payload.get("result") not in {"effective","partially_effective","ineffective"}: raise ValueError("invalid validation result")
        body={"validation_id":str(uuid4()),"tenant_id":self.tenant_id,"independent":True,"human_validation":True,"validated_by":actor_id,"validated_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def assess_closure(self, payload: dict):
        result=closure_readiness(payload.get("commitment",{}),payload.get("milestones",[]),payload.get("evidence",[]),payload.get("validations",[]),payload.get("dependencies",[]),payload.get("follow_ups",[]),payload.get("entity_checks",[]))
        return {"assessment_id":str(uuid4()),"tenant_id":self.tenant_id,"assessed_at":self._now(),"recommendation_only":True,**result}
    def certify_closure(self, actor_id: str, commitment_id: str, payload: dict):
        if payload.get("reviewer_role") not in CLOSURE_CERTIFIER_ROLES: raise PermissionError("authorized human closure certifier required")
        readiness=closure_readiness(payload.get("commitment",{}),payload.get("milestones",[]),payload.get("evidence",[]),payload.get("validations",[]),payload.get("dependencies",[]),payload.get("follow_ups",[]),payload.get("entity_checks",[]))
        if payload.get("decision")=="certify_closed" and not readiness["ready"]: raise ValueError("commitment is not closure-ready: "+";".join(readiness["blockers"]))
        if payload.get("decision") not in {"certify_closed","reject","changes_requested"}: raise ValueError("invalid closure decision")
        body={"closure_version_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_certification":True,"status":"certified_closed" if payload["decision"]=="certify_closed" else "closure_review","certified_by":actor_id,"certified_at":self._now(),"readiness":readiness,**payload}; body["version_hash"]=version_hash(body); return body
    def record_sustainability_observation(self, actor_id: str, payload: dict):
        body={"observation_id":str(uuid4()),"tenant_id":self.tenant_id,"recorded_by":actor_id,"recorded_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def evaluate_sustainability(self, observations: list[dict], min_window_days: int=30): return {**sustainability_state(observations,min_window_days),"monitoring_only":True,"human_reopen_decision_required":True}
    def detect_recurrence(self, commitment: dict, signals: list[dict]): return {"matches":recurrence_match(commitment,signals),"recommendation_only":True,"human_reopen_decision_required":True}
    def decide_reopen(self, actor_id: str, commitment_id: str, payload: dict):
        if payload.get("reviewer_role") not in REOPEN_REVIEW_ROLES: raise PermissionError("authorized human reopen reviewer required")
        if payload.get("decision") not in {"reopen","dismiss","continue_monitoring"}: raise ValueError("invalid reopen decision")
        return {"reopen_decision_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_decision":True,"reopened":payload["decision"]=="reopen","decided_by":actor_id,"decided_at":self._now(),**payload}
