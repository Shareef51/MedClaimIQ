from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_predictive_assurance import REGULATORY_PREDICTIVE_ASSURANCE_AUTHORITY
from app.models.regulatory_predictive_assurance import *
from app.repositories.regulatory_predictive_assurance import RegulatoryPredictiveAssuranceRepository
from app.repositories.regulatory_portfolio_oversight import RegulatoryPortfolioOversightRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _clamp(v):return max(0,min(100,round(v)))

class RegulatoryPredictiveAssuranceService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}; PREP_ROLES=READ_ROLES; REVIEW_ROLES={"auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryPredictiveAssuranceRepository(session,tenant_id);self.portfolio=RegulatoryPortfolioOversightRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _read(self,u):return self._role(u,self.READ_ROLES,"predictive regulatory oversight read role required")
    def _prep(self,u):return self._role(u,self.PREP_ROLES,"authorized human forecast preparer required")
    def _review(self,u):return self._role(u,self.REVIEW_ROLES,"authorized human predictive-risk reviewer required")
    def create_forecast(self,user_id,*,snapshot_id,horizon_days,model_version):
        self._prep(user_id);s=self.portfolio.snapshot(snapshot_id)
        if s is None:raise LookupError("regulatory portfolio snapshot not found")
        prior=self.repo.forecasts(snapshot_id);version=len(prior)+1
        failure=_clamp(s.portfolio_risk_score*0.58+s.overdue_task_count*4+s.systemic_cluster_count*3)
        deadline=_clamp(s.portfolio_risk_score*0.45+s.overdue_task_count*7+s.repeat_finding_count*2)
        recurrence=_clamp(s.recurring_root_cause_count*12+s.repeat_finding_count*10+s.systemic_cluster_count*4)
        deterioration=_clamp((100-s.control_effectiveness_pct)*0.7+s.systemic_cluster_count*5)
        readiness=_clamp(100-(failure*.28+deadline*.25+recurrence*.17+deterioration*.20))
        drivers=[{"key":"portfolio_risk","value":s.portfolio_risk_score},{"key":"overdue_tasks","value":s.overdue_task_count},{"key":"systemic_clusters","value":s.systemic_cluster_count},{"key":"control_effectiveness_pct","value":s.control_effectiveness_pct}]
        watermark=_sha({"snapshot":s.snapshot_id,"snapshot_version":s.snapshot_version,"source":s.source_watermark_sha256,"metrics":drivers})
        row=self.repo.add(RegulatoryPredictiveForecastModel(forecast_id=f"rpf_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=snapshot_id,forecast_version=version,horizon_days=horizon_days,model_version=model_version,remediation_failure_risk=failure,deadline_breach_risk=deadline,recurrence_risk=recurrence,control_deterioration_risk=deterioration,assurance_readiness_forecast=readiness,drivers=drivers,explanation={"method":"transparent deterministic baseline + governed model slot","recommendation_only":True,"human_review_required":True,"authority":REGULATORY_PREDICTIVE_ASSURANCE_AUTHORITY},source_watermark_sha256=watermark,prepared_by_user_id=user_id,created_at=_now()))
        return row
    def simulate(self,forecast_id,user_id,*,scenario_key,scenario_type,assumptions):
        self._prep(user_id);f=self.repo.forecast(forecast_id)
        if f is None:raise LookupError("predictive forecast not found")
        allowed={"dependency_delay","capacity_reduction","control_failure","accelerated_remediation","deadline_change","retest_failure"}
        if scenario_type not in allowed:raise ReviewConflictError("unsupported governed scenario type")
        delay=max(0,int(assumptions.get("delay_days",0)));capacity=float(assumptions.get("capacity_change_pct",0));failed=max(0,int(assumptions.get("failed_controls",0)))
        delta=min(35,delay/10+failed*6+max(0,-capacity)*0.25)
        projected={"remediation_failure_risk":_clamp(f.remediation_failure_risk+delta),"deadline_breach_risk":_clamp(f.deadline_breach_risk+delay/5+max(0,-capacity)*0.3),"assurance_readiness_forecast":_clamp(f.assurance_readiness_forecast-delta*.7),"delta_risk":round(delta,2)}
        recommendation={"recommendation_only":True,"action":"Route scenario to authorized human remediation leadership for prioritization and evidence-backed decision.","no_automatic_commitment_change":True}
        payload={"scenario":scenario_key,"type":scenario_type,"assumptions":assumptions,"projected":projected}
        return self.repo.add(RegulatoryScenarioSimulationModel(simulation_id=f"rss_{uuid4().hex}",tenant_id=self.tenant_id,forecast_id=forecast_id,scenario_key=scenario_key,scenario_type=scenario_type,assumptions=assumptions,projected_metrics=projected,recommendation=recommendation,payload_sha256=_sha(payload),created_by_user_id=user_id,created_at=_now()))
    def review_forecast(self,forecast_id,user_id,*,disposition,rationale,selected_management_actions):
        self._review(user_id);f=self.repo.forecast(forecast_id)
        if f is None:raise LookupError("predictive forecast not found")
        if disposition not in {"acknowledged","accepted_for_planning","rejected","needs_more_evidence"}:raise ReviewConflictError("invalid human review disposition")
        seq=len(self.repo.reviews(forecast_id))+1
        return self.repo.add(RegulatoryPredictiveReviewModel(review_id=f"rpr_{uuid4().hex}",tenant_id=self.tenant_id,forecast_id=forecast_id,review_sequence=seq,disposition=disposition,rationale=rationale,selected_management_actions=selected_management_actions,reviewed_by_user_id=user_id,reviewed_at=_now()))
    def view(self,forecast_id,user_id):
        self._read(user_id);f=self.repo.forecast(forecast_id)
        if f is None:raise LookupError("predictive forecast not found")
        return {"forecast_id":f.forecast_id,"snapshot_id":f.snapshot_id,"version":f.forecast_version,"horizon_days":f.horizon_days,"model_version":f.model_version,"risks":{"remediation_failure":f.remediation_failure_risk,"deadline_breach":f.deadline_breach_risk,"recurrence":f.recurrence_risk,"control_deterioration":f.control_deterioration_risk},"assurance_readiness_forecast":f.assurance_readiness_forecast,"drivers":f.drivers,"explanation":f.explanation,"source_watermark_sha256":f.source_watermark_sha256,"scenarios":[{"simulation_id":x.simulation_id,"scenario_key":x.scenario_key,"scenario_type":x.scenario_type,"projected_metrics":x.projected_metrics,"recommendation":x.recommendation} for x in self.repo.scenarios(forecast_id)],"human_reviews":[{"sequence":x.review_sequence,"disposition":x.disposition,"rationale":x.rationale,"reviewed_by":x.reviewed_by_user_id} for x in self.repo.reviews(forecast_id)],"authority":REGULATORY_PREDICTIVE_ASSURANCE_AUTHORITY}
    def dashboard(self,user_id):
        self._read(user_id);rows=self.repo.forecasts();latest={}
        for r in rows:latest.setdefault(r.snapshot_id,r)
        vals=list(latest.values())
        return {"forecast_count":len(vals),"high_failure_risk":sum(x.remediation_failure_risk>=70 for x in vals),"high_deadline_risk":sum(x.deadline_breach_risk>=70 for x in vals),"average_assurance_readiness":round(sum(x.assurance_readiness_forecast for x in vals)/len(vals)) if vals else 100,"recommendation_only":True}
