from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_deficiency_lifecycle import REGULATORY_DEFICIENCY_LIFECYCLE_AUTHORITY
from app.models.regulatory_deficiency_lifecycle import *
from app.repositories.regulatory_deficiency_lifecycle import RegulatoryDeficiencyLifecycleRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)

class RegulatoryDeficiencyLifecycleService:
    READ={"auditor","tenant_admin","accounting_controller"}; PREP=READ; INDEPENDENT={"auditor"}; EXECUTIVE={"tenant_admin","accounting_controller"}
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; self.repo=RegulatoryDeficiencyLifecycleRepository(session,tenant_id); self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed: raise ReviewConflictError(msg)
        return m
    def investigate(self,user_id,**p):
        self._role(user_id,self.PREP,"authorized deficiency investigator required")
        return self.repo.add(RegulatoryDeficiencyInvestigationModel(investigation_id=f"rdi_{uuid4().hex}",tenant_id=self.tenant_id,status="under_review",created_by_user_id=user_id,created_at=_now(),**p))
    def disposition(self,user_id,deficiency_key,*,classification,rationale,independent_challenge):
        self._role(user_id,self.INDEPENDENT,"independent human deficiency classification required")
        version=len(self.repo.dispositions(deficiency_key))+1
        if classification in {"material_weakness","significant_deficiency"} and not independent_challenge:
            raise ReviewConflictError("independent challenge evidence is required for formal significant classifications")
        return self.repo.add(RegulatoryDeficiencyDispositionModel(disposition_id=f"rdd_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,version=version,classification=classification,rationale=rationale,independent_challenge=independent_challenge,decided_by_user_id=user_id,decided_at=_now()))
    def create_plan(self,user_id,**p):
        self._role(user_id,self.PREP,"authorized corrective-action planner required")
        if p["due_at"] <= _now(): raise ValueError("corrective-action due_at must be in the future")
        return self.repo.add(RegulatoryCorrectiveActionPlanModel(plan_id=f"rcap_{uuid4().hex}",tenant_id=self.tenant_id,status="proposed",approved_by_user_id=None,approved_at=None,created_at=_now(),**p))
    def approve_plan(self,user_id,plan_id):
        self._role(user_id,self.EXECUTIVE,"human executive corrective-action approval required")
        plan=self.repo.plan(plan_id)
        if plan is None: raise LookupError("corrective-action plan not found")
        if plan.owner_user_id==user_id: raise ReviewConflictError("segregation of duties: plan owner cannot approve own plan")
        plan.status="approved"; plan.approved_by_user_id=user_id; plan.approved_at=_now(); self.session.flush(); return plan
    def attest(self,user_id,deficiency_key,*,conclusion,independent_validation_refs,retest_refs,rationale):
        self._role(user_id,self.EXECUTIVE,"authorized human executive attestation required")
        if conclusion=="closed" and (not independent_validation_refs or not retest_refs): raise ReviewConflictError("closure requires independent validation and retest evidence")
        version=len(self.repo.attestations(deficiency_key))+1
        return self.repo.add(RegulatoryExecutiveAttestationModel(attestation_id=f"rea_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,version=version,conclusion=conclusion,independent_validation_refs=independent_validation_refs,retest_refs=retest_refs,rationale=rationale,human_attestation=True,attested_by_user_id=user_id,attested_at=_now()))
    def dashboard(self,user_id):
        self._role(user_id,self.READ,"deficiency lifecycle read role required"); now=_now(); plans=self.repo.plans(); inv=self.repo.investigations()
        return {"investigations":len(inv),"material_weakness_candidates":sum(x.candidate_classification=="material_weakness_candidate" for x in inv),"open_plans":sum(p.status not in {"closed","cancelled"} for p in plans),"overdue_plans":sum(p.status not in {"closed","cancelled"} and p.due_at<now for p in plans),"expired_compensating_controls":sum(bool(p.compensating_control.get("expires_at")) and str(p.compensating_control.get("expires_at")) < now.isoformat() for p in plans),"authority":REGULATORY_DEFICIENCY_LIFECYCLE_AUTHORITY}
