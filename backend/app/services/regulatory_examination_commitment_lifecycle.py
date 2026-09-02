from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_commitment_lifecycle import version_hash,due_state,reconciliation_flags,completion_readiness,cross_examination_clusters

HUMAN_CERTIFIER_ROLES={"regulatory_affairs","compliance_reviewer","legal_reviewer","executive_certifier"}
AMENDMENT_REVIEW_ROLES={"regulatory_affairs","legal_reviewer","compliance_reviewer"}

class RegulatoryExaminationCommitmentLifecycleService:
    """Confirmed commitments become governed records; AI/workers may monitor but never certify completion."""
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def register(self,actor_id:str,payload:dict):
        body={"commitment_register_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"confirmed","binding":True,"created_by":actor_id,"created_at":self._now(),**payload}
        body["due_state"]=due_state(body.get("due_at")); body["version_hash"]=version_hash(body); return body
    def add_milestone(self,actor_id:str,payload:dict):
        body={"milestone_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"planned","created_by":actor_id,"created_at":self._now(),**payload}
        body["due_state"]=due_state(body.get("due_at")); body["version_hash"]=version_hash(body); return body
    def link_evidence(self,actor_id:str,payload:dict):
        if len(payload.get("sha256",''))!=64: raise ValueError("valid SHA-256 evidence hash required")
        body={"link_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"active","linked_by":actor_id,"linked_at":self._now(),**payload}; body["version_hash"]=version_hash(body); return body
    def validate_effectiveness(self,actor_id:str,payload:dict):
        if payload.get("validator_role") not in {"independent_validator","internal_auditor","compliance_reviewer"}: raise PermissionError("independent or authorized human validator required")
        if payload.get("result") not in {"effective","partially_effective","ineffective"}: raise ValueError("invalid effectiveness result")
        return {"validation_id":str(uuid4()),"tenant_id":self.tenant_id,"human_validation":True,"validated_at":self._now(),**payload}
    def reconcile(self,payload:dict): return {"flags":reconciliation_flags(payload["commitment"],payload.get("written_records",[])),"human_review_required":True}
    def request_amendment(self,actor_id:str,payload:dict):
        if payload.get("reviewer_role") not in AMENDMENT_REVIEW_ROLES: raise PermissionError("authorized human amendment reviewer required")
        return {"amendment_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"pending_human_approval","binding_change_applied":False,"created_by":actor_id,"created_at":self._now(),**payload}
    def certify_completion(self,actor_id:str,commitment_id:str,payload:dict,commitment:dict|None=None):
        if payload.get("reviewer_role") not in HUMAN_CERTIFIER_ROLES: raise PermissionError("authorized human completion certifier required")
        if payload.get("decision") not in {"certify_complete","reject","changes_requested"}: raise ValueError("invalid certification decision")
        readiness=completion_readiness(commitment or {},payload.get("milestones",[]),payload.get("evidence",[]),payload.get("validations",[]))
        if payload["decision"]=="certify_complete" and not readiness["ready"]: raise ValueError("commitment is not ready for completion certification: "+";".join(readiness["blockers"]))
        return {"certification_id":str(uuid4()),"commitment_id":commitment_id,"tenant_id":self.tenant_id,"human_certification":True,"status":"completed" if payload["decision"]=="certify_complete" else "completion_review","certified_by":actor_id,"certified_at":self._now(),"readiness":readiness,**payload}
    def create_follow_up(self,actor_id:str,payload:dict):
        body={"follow_up_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"open","created_by":actor_id,"created_at":self._now(),**payload}; body["due_state"]=due_state(body.get("due_at")); return body
    def correlate(self,commitments:list[dict]): return {"clusters":cross_examination_clusters(commitments),"recommendation_only":True,"human_review_required":True}
