from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_continuous_assurance import *

class RegulatoryContinuousAssuranceRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def observations(self,forecast_id=None):
        q=select(RegulatoryAssuranceObservationModel).where(RegulatoryAssuranceObservationModel.tenant_id==self.tenant_id)
        if forecast_id:q=q.where(RegulatoryAssuranceObservationModel.forecast_id==forecast_id)
        return list(self.session.scalars(q.order_by(RegulatoryAssuranceObservationModel.observed_at.desc())))
    def observation(self,observation_id):return self.session.scalar(select(RegulatoryAssuranceObservationModel).where(RegulatoryAssuranceObservationModel.tenant_id==self.tenant_id,RegulatoryAssuranceObservationModel.observation_id==observation_id))
    def drift(self,drift_event_id):return self.session.scalar(select(RegulatoryControlDriftEventModel).where(RegulatoryControlDriftEventModel.tenant_id==self.tenant_id,RegulatoryControlDriftEventModel.drift_event_id==drift_event_id))
    def drifts(self,status=None):
        q=select(RegulatoryControlDriftEventModel).where(RegulatoryControlDriftEventModel.tenant_id==self.tenant_id)
        if status:q=q.where(RegulatoryControlDriftEventModel.status==status)
        return list(self.session.scalars(q.order_by(RegulatoryControlDriftEventModel.detected_at.desc())))
    def warnings(self):return list(self.session.scalars(select(RegulatoryEarlyWarningModel).where(RegulatoryEarlyWarningModel.tenant_id==self.tenant_id).order_by(RegulatoryEarlyWarningModel.emitted_at.desc())))
    def investigations(self,drift_event_id):return list(self.session.scalars(select(RegulatoryAssuranceInvestigationModel).where(RegulatoryAssuranceInvestigationModel.tenant_id==self.tenant_id,RegulatoryAssuranceInvestigationModel.drift_event_id==drift_event_id).order_by(RegulatoryAssuranceInvestigationModel.review_sequence)))
