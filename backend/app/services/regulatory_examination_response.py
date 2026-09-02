from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_response import evidence_refresh_status, detect_response_contradictions, immutable_revision_hash, reconciliation_status

class RegulatoryExaminationResponseService:
    """Tenant-scoped orchestration service. AI creates recommendations/drafts only; approval/transmission remain human controlled."""
    def __init__(self, db, tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def intake_question(self, actor_id:str, payload:dict):
        return {"question_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"received","created_by":actor_id,"created_at":self._now(),**payload}
    def refresh_evidence(self, payload:dict): return {"question_id":payload["question_id"],**evidence_refresh_status(payload["evidence"],payload["current_versions"])}
    def create_revision(self, actor_id:str, payload:dict, prior_responses:list[dict]|None=None):
        contradictions=detect_response_contradictions(payload["text"], prior_responses or [])
        body={"revision_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"draft","created_by":actor_id,"created_at":self._now(),"contradictions":contradictions,**payload}
        body["revision_hash"]=immutable_revision_hash(body)
        body["ai_generated_or_assisted"]=True
        body["requires_human_approval"]=True
        return body
    def review_revision(self, actor_id:str, revision_id:str, decision:str, role:str, rationale:str):
        if role not in {"legal_reviewer","compliance_reviewer","regulatory_affairs","authorized_submitter"}: raise PermissionError("authorized human review role required")
        if decision not in {"approve","reject","changes_requested"}: raise ValueError("invalid decision")
        return {"revision_id":revision_id,"decision":decision,"reviewed_by":actor_id,"reviewer_role":role,"rationale":rationale,"reviewed_at":self._now(),"human_decision":True}
    def authorize_submission(self, actor_id:str, payload:dict, role:str):
        if role != "authorized_submitter": raise PermissionError("authorized_submitter role required")
        if not payload.get("human_approved"): raise PermissionError("human-approved revision required")
        return {"submission_id":str(uuid4()),"tenant_id":self.tenant_id,"authorized_by":actor_id,"human_authorized":True,"automated_transmission_allowed":False,"created_at":self._now(),**payload}
    def record_receipt(self, actor_id:str, payload:dict): return {"receipt_id":str(uuid4()),"tenant_id":self.tenant_id,"recorded_by":actor_id,"recorded_at":self._now(),**payload}
    def reconcile(self, submission:dict, receipt:dict|None, followups:list[dict]): return reconciliation_status(submission,receipt,followups)
