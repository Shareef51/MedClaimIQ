from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_post_closure_surveillance import POST_CLOSURE_AUTHORITY
from app.models.regulatory_post_closure_surveillance import *
from app.repositories.regulatory_post_closure_surveillance import RegulatoryPostClosureSurveillanceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)

class RegulatoryPostClosureSurveillanceService:
    READ={"auditor","tenant_admin","accounting_controller"}; MONITOR=READ; EXECUTIVE={"tenant_admin","accounting_controller"}
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; self.repo=RegulatoryPostClosureSurveillanceRepository(session,tenant_id); self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed: raise ReviewConflictError(msg)
        return m
    @staticmethod
    def composite_recurrence_score(*,recurrence_score,sustainability_decay_score,control_regression_score,cross_entity_count=0):
        base=(recurrence_score*0.45)+(sustainability_decay_score*0.25)+(control_regression_score*0.30)
        return round(min(1.0,base + min(cross_entity_count,5)*0.03),4)
    def record_signal(self,user_id,**p):
        self._role(user_id,self.MONITOR,"authorized post-closure monitoring role required")
        score=self.composite_recurrence_score(recurrence_score=p["recurrence_score"],sustainability_decay_score=p["sustainability_decay_score"],control_regression_score=p["control_regression_score"],cross_entity_count=len(p.get("cross_entity_keys",[])))
        status="reopen_candidate" if score>=0.75 else "investigate" if score>=0.5 else "observed"
        return self.repo.add(PostClosureSurveillanceSignalModel(signal_id=f"pcs_{uuid4().hex}",tenant_id=self.tenant_id,status=status,detected_at=_now(),**p))
    def create_candidate(self,user_id,**p):
        self._role(user_id,self.MONITOR,"authorized recurrence analyst required")
        version=len(self.repo.candidates(p["deficiency_key"]))+1
        return self.repo.add(RegulatoryReopenCandidateModel(candidate_id=f"rrc_{uuid4().hex}",tenant_id=self.tenant_id,version=version,human_decision_required=True,status="pending_human_review",created_at=_now(),**p))
    def decide_reopen(self,user_id,candidate_id,*,decision,rationale,renewed_corrective_action_refs):
        self._role(user_id,self.EXECUTIVE,"authorized human reopening authority required")
        c=self.repo.candidate(candidate_id)
        if c is None: raise LookupError("reopen candidate not found")
        if decision=="reopen" and not c.recurrence_evidence_refs: raise ReviewConflictError("reopening requires recurrence evidence")
        if decision=="reopen" and not renewed_corrective_action_refs and not c.renewed_corrective_action_refs: raise ReviewConflictError("reopening requires renewed corrective-action linkage")
        c.status="reopened" if decision=="reopen" else "closed_no_reopen" if decision=="keep_closed" else "monitoring"
        self.session.flush()
        return self.repo.add(ReopenedIssueInvestigationModel(investigation_id=f"rii_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=c.deficiency_key,candidate_id=c.candidate_id,decision=decision,rationale=rationale,renewed_corrective_action_refs=renewed_corrective_action_refs or c.renewed_corrective_action_refs,revalidation_required=decision=="reopen",decided_by_user_id=user_id,decided_at=_now()))
    def dashboard(self,user_id):
        self._role(user_id,self.READ,"post-closure surveillance read role required")
        sig=self.repo.signals(); cand=self.repo.candidates(); inv=self.repo.investigations()
        return {"signals":len(sig),"reopen_candidate_signals":sum(s.status=="reopen_candidate" for s in sig),"candidates":len(cand),"pending_human_review":sum(c.status=="pending_human_review" for c in cand),"reopened":sum(i.decision=="reopen" for i in inv),"authority":POST_CLOSURE_AUTHORITY}
