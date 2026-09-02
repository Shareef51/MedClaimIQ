from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class RegulatoryAssuranceObservationModel(Base):
    __tablename__="regulatory_assurance_observations"
    __table_args__=(UniqueConstraint("tenant_id","forecast_id","observation_key","observed_at",name="uq_reg_assurance_observation"),)
    observation_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    forecast_id:Mapped[str]=mapped_column(ForeignKey("regulatory_predictive_forecasts.forecast_id",ondelete="RESTRICT"),nullable=False,index=True)
    observation_key:Mapped[str]=mapped_column(String(140),nullable=False)
    signal_type:Mapped[str]=mapped_column(String(80),nullable=False)
    control_id:Mapped[str|None]=mapped_column(String(128),nullable=True,index=True)
    finding_id:Mapped[str|None]=mapped_column(String(128),nullable=True,index=True)
    commitment_id:Mapped[str|None]=mapped_column(String(128),nullable=True,index=True)
    observed_value:Mapped[int]=mapped_column(Integer,nullable=False)
    expected_value:Mapped[int]=mapped_column(Integer,nullable=False)
    evidence_age_days:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    evidence_refs:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    source_watermark_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    recorded_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)

class RegulatoryControlDriftEventModel(Base):
    __tablename__="regulatory_control_drift_events"
    drift_event_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    observation_id:Mapped[str]=mapped_column(ForeignKey("regulatory_assurance_observations.observation_id",ondelete="RESTRICT"),nullable=False,index=True)
    severity:Mapped[str]=mapped_column(String(24),nullable=False,index=True)
    drift_score:Mapped[int]=mapped_column(Integer,nullable=False)
    threshold_version:Mapped[str]=mapped_column(String(80),nullable=False)
    indicators:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    recommendation:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    status:Mapped[str]=mapped_column(String(32),nullable=False,default="open")
    detected_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryEarlyWarningModel(Base):
    __tablename__="regulatory_early_warnings"
    warning_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    drift_event_id:Mapped[str]=mapped_column(ForeignKey("regulatory_control_drift_events.drift_event_id",ondelete="CASCADE"),nullable=False,index=True)
    warning_type:Mapped[str]=mapped_column(String(80),nullable=False)
    priority:Mapped[str]=mapped_column(String(24),nullable=False)
    message:Mapped[str]=mapped_column(Text,nullable=False)
    requires_human_investigation:Mapped[bool]=mapped_column(nullable=False,default=True)
    emitted_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class RegulatoryAssuranceInvestigationModel(Base):
    __tablename__="regulatory_assurance_investigations"
    __table_args__=(UniqueConstraint("tenant_id","drift_event_id","review_sequence",name="uq_reg_assurance_investigation_seq"),)
    investigation_id:Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id:Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    drift_event_id:Mapped[str]=mapped_column(ForeignKey("regulatory_control_drift_events.drift_event_id",ondelete="RESTRICT"),nullable=False,index=True)
    review_sequence:Mapped[int]=mapped_column(Integer,nullable=False)
    disposition:Mapped[str]=mapped_column(String(40),nullable=False)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    corrective_response:Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    reviewed_by_user_id:Mapped[str]=mapped_column(ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False)
    reviewed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
