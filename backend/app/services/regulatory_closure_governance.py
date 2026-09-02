from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_closure_governance import REGULATORY_CLOSURE_AUTHORITY
from app.models.regulatory_closure_governance import *
from app.repositories.regulatory_closure_governance import RegulatoryClosureGovernanceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)

class RegulatoryClosureGovernanceService:
    READ={"auditor","tenant_admin","accounting_controller"}; PREP=READ; INDEPENDENT={"auditor"}; EXECUTIVE={"tenant_admin","accounting_controller"}
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; self.repo=RegulatoryClosureGovernanceRepository(session,tenant_id); self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed: raise ReviewConflictError(msg)
        return m
    @staticmethod
    def readiness_score(*,corrective_action_refs,retest_refs,independent_validation_refs,unresolved_exceptions,compensating_control_exit,residual_risk):
        score=0
        score += 25 if corrective_action_refs else 0
        score += 25 if retest_refs else 0
        score += 25 if independent_validation_refs else 0
        score += 10 if not unresolved_exceptions else 0
        score += 10 if compensating_control_exit.get("validated") is True else 0
        score += 5 if residual_risk.get("human_accepted") is True else 0
        return score
    def create_package(self,user_id,**p):
        self._role(user_id,self.PREP,"authorized closure package preparer required")
        score=self.readiness_score(**{k:p[k] for k in ["corrective_action_refs","retest_refs","independent_validation_refs","unresolved_exceptions","compensating_control_exit","residual_risk"]})
        return self.repo.add(RegulatoryClosurePackageModel(package_id=f"rcp_{uuid4().hex}",tenant_id=self.tenant_id,readiness_score=score,status="ready_for_review" if score==100 else "blocked",created_by_user_id=user_id,created_at=_now(),**p))
    def certify(self,user_id,package_id,*,conclusion,rationale):
        self._role(user_id,self.EXECUTIVE,"authorized human executive certification required")
        pkg=self.repo.package(package_id)
        if pkg is None: raise LookupError("closure package not found")
        if pkg.created_by_user_id==user_id: raise ReviewConflictError("segregation of duties: package preparer cannot certify own package")
        if conclusion=="certified_closed" and pkg.readiness_score<100: raise ReviewConflictError("closure certification blocked until readiness score is 100")
        version=len(self.repo.certifications(pkg.deficiency_key))+1
        pkg.status="certified" if conclusion=="certified_closed" else "reviewed"
        return self.repo.add(RegulatoryClosureCertificationModel(certification_id=f"rcc_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=pkg.deficiency_key,version=version,conclusion=conclusion,rationale=rationale,human_certification=True,certified_by_user_id=user_id,certified_at=_now()))
    def start_sustainability(self,user_id,*,deficiency_key,starts_at,ends_at,required_observations):
        self._role(user_id,self.INDEPENDENT,"independent assurance role required")
        if ends_at<=starts_at: raise ValueError("sustainability end must be after start")
        return self.repo.add(RegulatorySustainabilityWindowModel(window_id=f"rsw_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,starts_at=starts_at,ends_at=ends_at,required_observations=required_observations,observed_passes=0,recurrence_detected=False,status="monitoring",created_at=_now()))
    def observe(self,user_id,window_id,*,passed,recurrence_detected=False):
        self._role(user_id,self.INDEPENDENT,"independent assurance observation required")
        w=self.repo.window(window_id)
        if w is None: raise LookupError("sustainability window not found")
        if passed: w.observed_passes += 1
        if recurrence_detected: w.recurrence_detected=True; w.status="reopen_candidate"
        elif w.observed_passes>=w.required_observations and _now()>=w.ends_at: w.status="sustained"
        self.session.flush(); return w
    def reopen_decision(self,user_id,deficiency_key,*,trigger,evidence_refs,decision,rationale):
        self._role(user_id,self.EXECUTIVE,"authorized human reopen decision required")
        return self.repo.add(RegulatoryReopenDecisionModel(decision_id=f"rrd_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,trigger=trigger,evidence_refs=evidence_refs,decision=decision,rationale=rationale,decided_by_user_id=user_id,decided_at=_now()))
    def dashboard(self,user_id):
        self._role(user_id,self.READ,"closure governance read role required")
        pkgs=self.repo.packages(); wins=self.repo.windows(); dec=self.repo.reopen_decisions()
        return {"packages":len(pkgs),"blocked_packages":sum(p.status=="blocked" for p in pkgs),"certified_packages":sum(p.status=="certified" for p in pkgs),"sustainability_windows":len(wins),"reopen_candidates":sum(w.status=="reopen_candidate" for w in wins),"reopen_decisions":len(dec),"authority":REGULATORY_CLOSURE_AUTHORITY}
