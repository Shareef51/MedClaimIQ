from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryPredictiveForecastModel(Base):
    __tablename__="regulatory_predictive_forecasts"
    __table_args__=(UniqueConstraint("tenant_id","snapshot_id","forecast_version",name="uq_reg_predictive_forecast_version"),)
    forecast_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    snapshot_id:Mapped[str]=mapped_column(ForeignKey("regulatory_portfolio_snapshots.snapshot_id",ondelete="RESTRICT"),nullable=False,index=True)
    forecast_version:Mapped[int]=mapped_column(Integer,nullable=False)
    horizon_days:Mapped[int]=mapped_column(Integer,nullable=False)
    model_version:Mapped[str]=mapped_column(String(120),nullable=False)
    remediation_failure_risk:Mapped[int]=mapped_column(Integer,nullable=False)
    deadline_breach_risk:Mapped[int]=mapped_column(Integer,nullable=False)
    recurrence_risk:Mapped[int]=mapped_column(Integer,nullable=False)
    control_deterioration_risk:Mapped[int]=mapped_column(Integer,nullable=False)
    assurance_readiness_forecast:Mapped[int]=mapped_column(Integer,nullable=False)
    drivers:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    explanation:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    source_watermark_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    prepared_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryScenarioSimulationModel(Base):
    __tablename__="regulatory_scenario_simulations"
    __table_args__=(UniqueConstraint("tenant_id","forecast_id","scenario_key",name="uq_reg_scenario_key"),)
    simulation_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    forecast_id:Mapped[str]=mapped_column(ForeignKey("regulatory_predictive_forecasts.forecast_id",ondelete="CASCADE"),nullable=False,index=True)
    scenario_key:Mapped[str]=mapped_column(String(140),nullable=False)
    scenario_type:Mapped[str]=mapped_column(String(60),nullable=False)
    assumptions:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    projected_metrics:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    recommendation:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    payload_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    created_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryPredictiveReviewModel(Base):
    __tablename__="regulatory_predictive_reviews"
    __table_args__=(UniqueConstraint("tenant_id","forecast_id","review_sequence",name="uq_reg_predictive_review_seq"),)
    review_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    forecast_id:Mapped[str]=mapped_column(ForeignKey("regulatory_predictive_forecasts.forecast_id",ondelete="CASCADE"),nullable=False,index=True)
    review_sequence:Mapped[int]=mapped_column(Integer,nullable=False)
    disposition:Mapped[str]=mapped_column(String(30),nullable=False)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    selected_management_actions:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    reviewed_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    reviewed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
