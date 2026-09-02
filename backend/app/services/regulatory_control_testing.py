from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_control_testing import REGULATORY_CONTROL_TESTING_AUTHORITY
from app.models.regulatory_control_testing import *
from app.repositories.regulatory_control_testing import RegulatoryControlTestingRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

class RegulatoryControlTestingService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}; PREP_ROLES=READ_ROLES; CONCLUDE_ROLES={"auditor"}
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryControlTestingRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    @staticmethod
    def select_risk_based_sample(population:list[dict],sample_size:int)->list[dict]:
        ranked=sorted(population,key=lambda x:(int(x.get("risk_score",0)),str(x.get("key",""))),reverse=True)
        return ranked[:min(sample_size,len(ranked))]
    def create_plan(self,user_id,*,control_id,test_type,frequency,sampling_strategy,evidence_requirements,independent_tester_role):
        self._role(user_id,self.PREP_ROLES,"authorized control test planner required")
        prior=[p for p in self.repo.plans() if p.control_id==control_id]
        v=max([p.plan_version for p in prior],default=0)+1
        return self.repo.add(RegulatoryControlTestPlanModel(test_plan_id=f"rctp_{uuid4().hex}",tenant_id=self.tenant_id,control_id=control_id,test_type=test_type,frequency=frequency,plan_version=v,sampling_strategy=sampling_strategy,evidence_requirements=evidence_requirements,independent_tester_role=independent_tester_role,active=True,created_by_user_id=user_id,created_at=_now()))
    def prepare_run(self,user_id,*,test_plan_id,test_window_start,test_window_end,population,sample_size):
        self._role(user_id,self.PREP_ROLES,"authorized test preparer required");plan=self.repo.plan(test_plan_id)
        if plan is None:raise LookupError("control test plan not found")
        if test_window_end<=test_window_start:raise ValueError("test window end must be after start")
        run=self.repo.add(RegulatoryControlTestRunModel(test_run_id=f"rctr_{uuid4().hex}",tenant_id=self.tenant_id,test_plan_id=plan.test_plan_id,control_id=plan.control_id,test_window_start=test_window_start,test_window_end=test_window_end,population_size=len(population),population_watermark_sha256=_sha(population),status="sampled",scheduled_retest_at=None,prepared_by_user_id=user_id,created_at=_now()))
        samples=[]
        for item in self.select_risk_based_sample(population,sample_size):
            samples.append(self.repo.add(RegulatoryEvidenceSampleModel(sample_id=f"res_{uuid4().hex}",tenant_id=self.tenant_id,test_run_id=run.test_run_id,sample_key=str(item.get("key") or item.get("id") or uuid4().hex),entity_id=item.get("entity_id"),risk_score=max(0,min(100,int(item.get("risk_score",0)))),selection_reason="risk-ranked deterministic selection",evidence_refs=item.get("evidence_refs",[]),provenance={"population_watermark_sha256":run.population_watermark_sha256,"source":item.get("source","governed_population"),"recommendation_only":True},result="pending",exception_code=None,tested_at=None)))
        return run,samples
    def record_sample_result(self,user_id,sample_id,*,result,evidence_refs,exception_code=None):
        self._role(user_id,self.PREP_ROLES,"authorized tester required");s=self.repo.sample(sample_id)
        if s is None:raise LookupError("evidence sample not found")
        s.result=result;s.evidence_refs=evidence_refs;s.exception_code=exception_code;s.tested_at=_now();self.session.flush();return s
    def conclude(self,user_id,test_run_id,*,effectiveness,rationale):
        reviewer=self._role(user_id,self.CONCLUDE_ROLES,"independent auditor conclusion required");run=self.repo.run(test_run_id)
        if run is None:raise LookupError("control test run not found")
        if run.prepared_by_user_id==user_id:raise ReviewConflictError("segregation of duties: test preparer cannot independently conclude the same run")
        samples=self.repo.samples(test_run_id)
        if not samples or any(s.result=="pending" for s in samples):raise ReviewConflictError("all sampled evidence must be tested before conclusion")
        seq=len(self.repo.conclusions(test_run_id))+1
        exceptions=[{"sample_id":s.sample_id,"result":s.result,"exception_code":s.exception_code} for s in samples if s.result!="pass"]
        row=self.repo.add(RegulatoryControlTestConclusionModel(conclusion_id=f"rctc_{uuid4().hex}",tenant_id=self.tenant_id,test_run_id=test_run_id,conclusion_version=seq,effectiveness=effectiveness,exception_summary=exceptions,rationale=rationale,independent=True,concluded_by_user_id=user_id,concluded_at=_now()))
        run.status="concluded";run.scheduled_retest_at=_now()+timedelta(days=30) if effectiveness in {"ineffective","effective_with_exceptions","inconclusive"} else None
        self.session.flush();return row
    def view_run(self,user_id,test_run_id):
        self._role(user_id,self.READ_ROLES,"control testing read role required");run=self.repo.run(test_run_id)
        if run is None:raise LookupError("control test run not found")
        samples=self.repo.samples(test_run_id);conclusions=self.repo.conclusions(test_run_id)
        return {"test_run_id":run.test_run_id,"control_id":run.control_id,"status":run.status,"population_size":run.population_size,"population_watermark_sha256":run.population_watermark_sha256,"samples":[{"sample_id":s.sample_id,"sample_key":s.sample_key,"entity_id":s.entity_id,"risk_score":s.risk_score,"result":s.result,"exception_code":s.exception_code,"provenance":s.provenance} for s in samples],"conclusions":[{"version":c.conclusion_version,"effectiveness":c.effectiveness,"independent":c.independent,"concluded_by":c.concluded_by_user_id} for c in conclusions],"authority":REGULATORY_CONTROL_TESTING_AUTHORITY}
    def dashboard(self,user_id):
        self._role(user_id,self.READ_ROLES,"control testing read role required");runs=self.repo.runs()
        return {"test_runs":len(runs),"open_runs":sum(r.status!="concluded" for r in runs),"concluded_runs":sum(r.status=="concluded" for r in runs),"retests_scheduled":sum(r.scheduled_retest_at is not None for r in runs),"orchestration_only":True}
