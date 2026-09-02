from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_interaction import provenance_hash,detect_commitment_candidates,separate_positions,contradiction_flags,commitment_due_state

class RegulatoryExaminationInteractionService:
    """Governed meeting intelligence. AI may extract/summarize; only humans may confirm commitments."""
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def create_meeting(self,actor_id:str,payload:dict):
        body={"meeting_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"scheduled","created_by":actor_id,"created_at":self._now(),**payload}
        body["version_hash"]=provenance_hash(body); return body
    def capture_statement(self,actor_id:str,payload:dict):
        if payload.get("classification") not in {"documented_regulator_position","enterprise_interpretation","ai_observation","enterprise_statement"}: raise ValueError("invalid statement classification")
        body={"statement_id":str(uuid4()),"tenant_id":self.tenant_id,"captured_by":actor_id,"captured_at":self._now(),**payload}
        body["provenance_hash"]=provenance_hash(body); return body
    def summarize(self,payload:dict):
        statements=payload.get("statements",[])
        return {"meeting_id":payload["meeting_id"],"position_separation":separate_positions(statements),"candidate_commitments":detect_commitment_candidates(statements),"contradictions":contradiction_flags(statements,payload.get("prior_submissions",[])),"ai_assisted":True,"requires_human_validation":True}
    def create_commitment_candidate(self,actor_id:str,payload:dict):
        return {"commitment_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"candidate","binding":False,"human_confirmation_required":True,"created_by":actor_id,"created_at":self._now(),**payload}
    def decide_commitment(self,actor_id:str,commitment_id:str,payload:dict):
        if payload.get("reviewer_role") not in {"regulatory_affairs","compliance_reviewer","legal_reviewer","executive_certifier"}: raise PermissionError("authorized human commitment reviewer required")
        if payload.get("decision") not in {"confirm","reject","changes_requested"}: raise ValueError("invalid decision")
        confirmed=payload["decision"]=="confirm"
        return {"commitment_id":commitment_id,"status":"confirmed" if confirmed else "rejected" if payload["decision"]=="reject" else "human_review","binding":confirmed,"human_decision":True,"decided_by":actor_id,"decided_at":self._now(),**payload}
    def create_action(self,actor_id:str,payload:dict):
        return {"action_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"open","created_by":actor_id,"created_at":self._now(),**payload,"due_state":commitment_due_state(payload.get("due_at"))}
