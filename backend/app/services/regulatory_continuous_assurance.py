from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_continuous_assurance import REGULATORY_CONTINUOUS_ASSURANCE_AUTHORITY
from app.models.regulatory_continuous_assurance import *
from app.repositories.regulatory_continuous_assurance import RegulatoryContinuousAssuranceRepository
from app.repositories.regulatory_predictive_assurance import RegulatoryPredictiveAssuranceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _clamp(v):return max(0,min(100,round(v)))

class RegulatoryContinuousAssuranceService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}; PREP_ROLES=READ_ROLES; REVIEW_ROLES={"auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryContinuousAssuranceRepository(session,tenant_id);self.predictive=RegulatoryPredictiveAssuranceRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _read(self,u):return self._role(u,self.READ_ROLES,"continuous assurance read role required")
    def _prep(self,u):return self._role(u,self.PREP_ROLES,"authorized assurance signal recorder required")
    def _review(self,u):return self._role(u,self.REVIEW_ROLES,"authorized human assurance investigator required")
    @staticmethod
    def drift_score(*,observed_value:int,expected_value:int,evidence_age_days:int,signal_type:str)->int:
        variance=abs(observed_value-expected_value)
        freshness=min(30,evidence_age_days//7)
        critical=12 if signal_type in {"control_test_failure","commitment_trajectory","recurrence_signal"} else 0
        return _clamp(variance*1.35+freshness+critical)
    @staticmethod
    def severity(score:int)->str:
        return "critical" if score>=80 else "high" if score>=60 else "moderate" if score>=35 else "low"
    def record_observation(self,user_id,*,forecast_id,observation_key,signal_type,control_id=None,finding_id=None,commitment_id=None,observed_value,expected_value,evidence_age_days,evidence_refs,observed_at,threshold_version):
        self._prep(user_id);forecast=self.predictive.forecast(forecast_id)
        if forecast is None:raise LookupError("predictive assurance forecast not found")
        watermark=_sha({"forecast_id":forecast_id,"forecast_watermark":forecast.source_watermark_sha256,"observation_key":observation_key,"observed_value":observed_value,"expected_value":expected_value,"evidence_refs":evidence_refs,"observed_at":observed_at})
        obs=self.repo.add(RegulatoryAssuranceObservationModel(observation_id=f"rao_{uuid4().hex}",tenant_id=self.tenant_id,forecast_id=forecast_id,observation_key=observation_key,signal_type=signal_type,control_id=control_id,finding_id=finding_id,commitment_id=commitment_id,observed_value=observed_value,expected_value=expected_value,evidence_age_days=evidence_age_days,evidence_refs=evidence_refs,source_watermark_sha256=watermark,observed_at=observed_at,recorded_by_user_id=user_id))
        score=self.drift_score(observed_value=observed_value,expected_value=expected_value,evidence_age_days=evidence_age_days,signal_type=signal_type);sev=self.severity(score)
        indicators=[{"key":"forecast_vs_actual_gap","value":abs(observed_value-expected_value)},{"key":"evidence_age_days","value":evidence_age_days},{"key":"signal_type","value":signal_type}]
        drift=self.repo.add(RegulatoryControlDriftEventModel(drift_event_id=f"rcd_{uuid4().hex}",tenant_id=self.tenant_id,observation_id=obs.observation_id,severity=sev,drift_score=score,threshold_version=threshold_version,indicators=indicators,recommendation={"recommendation_only":True,"action":"Investigate material drift and refresh supporting control evidence.","human_decision_required":sev in {"critical","high"},"authority":REGULATORY_CONTINUOUS_ASSURANCE_AUTHORITY},status="open",detected_at=_now()))
        warning=None
        if sev in {"critical","high"}:
            warning=self.repo.add(RegulatoryEarlyWarningModel(warning_id=f"rew_{uuid4().hex}",tenant_id=self.tenant_id,drift_event_id=drift.drift_event_id,warning_type="supervisory_control_drift",priority=sev,message=f"{sev.upper()} regulatory assurance drift detected for {observation_key}; human investigation required.",requires_human_investigation=True,emitted_at=_now()))
        return obs,drift,warning
    def investigate(self,drift_event_id,user_id,*,disposition,rationale,corrective_response):
        self._review(user_id);d=self.repo.drift(drift_event_id)
        if d is None:raise LookupError("control drift event not found")
        if disposition not in {"confirmed_drift","false_positive","monitor","needs_more_evidence","corrective_response_planned"}:raise ReviewConflictError("invalid continuous assurance disposition")
        seq=len(self.repo.investigations(drift_event_id))+1
        row=self.repo.add(RegulatoryAssuranceInvestigationModel(investigation_id=f"rai_{uuid4().hex}",tenant_id=self.tenant_id,drift_event_id=drift_event_id,review_sequence=seq,disposition=disposition,rationale=rationale,corrective_response=corrective_response,reviewed_by_user_id=user_id,reviewed_at=_now()))
        d.status="reviewed" if disposition!="monitor" else "monitoring"
        self.session.flush();return row
    def view_drift(self,drift_event_id,user_id):
        self._read(user_id);d=self.repo.drift(drift_event_id)
        if d is None:raise LookupError("control drift event not found")
        o=self.repo.observation(d.observation_id)
        return {"drift_event_id":d.drift_event_id,"severity":d.severity,"drift_score":d.drift_score,"status":d.status,"threshold_version":d.threshold_version,"indicators":d.indicators,"recommendation":d.recommendation,"observation":{"observation_id":o.observation_id,"forecast_id":o.forecast_id,"signal_type":o.signal_type,"observed_value":o.observed_value,"expected_value":o.expected_value,"evidence_age_days":o.evidence_age_days,"evidence_refs":o.evidence_refs,"source_watermark_sha256":o.source_watermark_sha256},"investigations":[{"sequence":x.review_sequence,"disposition":x.disposition,"rationale":x.rationale,"corrective_response":x.corrective_response,"reviewed_by":x.reviewed_by_user_id} for x in self.repo.investigations(drift_event_id)],"authority":REGULATORY_CONTINUOUS_ASSURANCE_AUTHORITY}
    def dashboard(self,user_id):
        self._read(user_id);drifts=self.repo.drifts();warnings=self.repo.warnings()
        return {"open_drift_events":sum(x.status in {"open","monitoring"} for x in drifts),"critical_drift_events":sum(x.severity=="critical" and x.status in {"open","monitoring"} for x in drifts),"high_drift_events":sum(x.severity=="high" and x.status in {"open","monitoring"} for x in drifts),"early_warnings":len(warnings),"stale_evidence_events":sum(any(i.get("key")=="evidence_age_days" and i.get("value",0)>30 for i in x.indicators) for x in drifts),"monitoring_only":True}
