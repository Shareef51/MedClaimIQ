from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_systemic_recurrence_portfolio import aggregate_systemic_patterns, supervisory_materiality_score, correlate_regulator_followups, version_hash

INTERVENTION_REVIEW_ROLES={"regulatory_affairs","executive_certifier","chief_compliance_officer","chief_risk_officer","internal_auditor"}
PROGRAM_APPROVER_ROLES={"executive_certifier","chief_compliance_officer","chief_risk_officer"}
AUDIT_ROLES={"internal_auditor"}

class RegulatoryExaminationSystemicRecurrencePortfolioService:
    def __init__(self, db, tenant_id: str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, body: dict): body["version_hash"]=version_hash(body); return body
    def aggregate(self, payload: dict):
        result=aggregate_systemic_patterns(payload.get("occurrences", []))
        followup=correlate_regulator_followups(payload.get("occurrences", []), payload.get("regulator_follow_ups", []))
        return self._immutable({"portfolio_snapshot_id":str(uuid4()),"tenant_id":self.tenant_id,"recommendation_only":True,"portfolio_id":payload["portfolio_id"],"assessment":result,"regulator_follow_up_correlation":followup,"created_at":self._now()})
    def materiality(self, payload: dict):
        return {"tenant_id":self.tenant_id,"recommendation_only":True,**supervisory_materiality_score(payload)}
    def create_intervention(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in INTERVENTION_REVIEW_ROLES: raise PermissionError("authorized human supervisory reviewer required")
        return self._immutable({"intervention_case_id":str(uuid4()),"tenant_id":self.tenant_id,"status":"under_human_review","human_decision":True,"program_approved":False,"created_by":actor_id,"created_at":self._now(),**payload})
    def decide_program(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in PROGRAM_APPROVER_ROLES: raise PermissionError("authorized human executive program approver required")
        if payload.get("decision") not in {"approve","reject","return_for_changes"}: raise ValueError("invalid intervention program decision")
        return self._immutable({"intervention_program_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_approval":False,"decided_by":actor_id,"decided_at":self._now(),**payload})
    def independent_challenge(self, actor_id: str, payload: dict):
        if payload.get("reviewer_role") not in AUDIT_ROLES: raise PermissionError("internal audit human reviewer required")
        return self._immutable({"challenge_version_id":str(uuid4()),"tenant_id":self.tenant_id,"independent_human_challenge":True,"created_by":actor_id,"created_at":self._now(),**payload})
