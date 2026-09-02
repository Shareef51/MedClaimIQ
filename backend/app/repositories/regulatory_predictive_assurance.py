from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_predictive_assurance import *

class RegulatoryPredictiveAssuranceRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def forecasts(self,snapshot_id=None):
        q=select(RegulatoryPredictiveForecastModel).where(RegulatoryPredictiveForecastModel.tenant_id==self.tenant_id)
        if snapshot_id:q=q.where(RegulatoryPredictiveForecastModel.snapshot_id==snapshot_id)
        return list(self.session.scalars(q.order_by(RegulatoryPredictiveForecastModel.created_at.desc())))
    def forecast(self,forecast_id):return self.session.scalar(select(RegulatoryPredictiveForecastModel).where(RegulatoryPredictiveForecastModel.tenant_id==self.tenant_id,RegulatoryPredictiveForecastModel.forecast_id==forecast_id))
    def scenarios(self,forecast_id):return list(self.session.scalars(select(RegulatoryScenarioSimulationModel).where(RegulatoryScenarioSimulationModel.tenant_id==self.tenant_id,RegulatoryScenarioSimulationModel.forecast_id==forecast_id).order_by(RegulatoryScenarioSimulationModel.created_at)))
    def reviews(self,forecast_id):return list(self.session.scalars(select(RegulatoryPredictiveReviewModel).where(RegulatoryPredictiveReviewModel.tenant_id==self.tenant_id,RegulatoryPredictiveReviewModel.forecast_id==forecast_id).order_by(RegulatoryPredictiveReviewModel.review_sequence)))
