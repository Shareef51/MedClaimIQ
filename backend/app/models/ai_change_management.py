from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class AIConfigurationSnapshotModel(TimestampMixin, Base):
    __tablename__ = "ai_configuration_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "config_key", "version", name="uq_ai_config_snapshot_version"),
        Index("ix_ai_config_snapshot_tenant_key_created", "tenant_id", "config_key", "created_at"),
    )
    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_type: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    evaluation_baseline_id: Mapped[str | None] = mapped_column(String(128))
    evaluation_run_id: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class AIEnvironmentAssignmentModel(TimestampMixin, Base):
    __tablename__ = "ai_environment_assignments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "environment", "config_key", name="uq_ai_environment_assignment"),
        Index("ix_ai_assignment_tenant_env", "tenant_id", "environment"),
    )
    assignment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    config_key: Mapped[str] = mapped_column(String(180), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False)
    assignment_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="promotion")
    activated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIConfigurationPromotionModel(TimestampMixin, Base):
    __tablename__ = "ai_configuration_promotions"
    __table_args__ = (Index("ix_ai_promotion_tenant_created", "tenant_id", "created_at"),)
    promotion_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False)
    config_key: Mapped[str] = mapped_column(String(180), nullable=False)
    target_environment: Mapped[str] = mapped_column(String(32), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approval_reason: Mapped[str | None] = mapped_column(String(1000))
    evaluation_run_id: Mapped[str | None] = mapped_column(String(128))
    evaluation_decision: Mapped[str | None] = mapped_column(String(20))
    previous_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIExperimentModel(TimestampMixin, Base):
    __tablename__ = "ai_experiments"
    __table_args__ = (UniqueConstraint("tenant_id", "experiment_key", name="uq_ai_experiment_key"),)
    experiment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_key: Mapped[str] = mapped_column(String(160), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    champion_snapshot_id: Mapped[str] = mapped_column(ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False)
    challenger_snapshot_id: Mapped[str] = mapped_column(ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False)
    challenger_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)
    shadow_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evaluation_baseline_id: Mapped[str | None] = mapped_column(String(128))
    guardrails: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class AIExperimentAssignmentModel(TimestampMixin, Base):
    __tablename__ = "ai_experiment_assignments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "experiment_id", "subject_sha256", name="uq_ai_experiment_subject"),
        Index("ix_ai_experiment_assignment", "tenant_id", "experiment_id"),
    )
    assignment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"), nullable=False)
    subject_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str] = mapped_column(String(24), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)


class AIExperimentObservationModel(TimestampMixin, Base):
    __tablename__ = "ai_experiment_observations"
    __table_args__ = (Index("ix_ai_experiment_observation", "tenant_id", "experiment_id", "created_at"),)
    observation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"), nullable=False)
    assignment_id: Mapped[str | None] = mapped_column(String(128))
    variant: Mapped[str] = mapped_column(String(24), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    evaluation_run_id: Mapped[str | None] = mapped_column(String(128))
    trace_id: Mapped[str | None] = mapped_column(String(64))
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class AIConfigurationDriftEventModel(TimestampMixin, Base):
    __tablename__ = "ai_configuration_drift_events"
    __table_args__ = (Index("ix_ai_drift_tenant_detected", "tenant_id", "created_at"),)
    drift_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    config_key: Mapped[str] = mapped_column(String(180), nullable=False)
    expected_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    detected_by: Mapped[str] = mapped_column(String(128), nullable=False)


class AIChangeEventModel(TimestampMixin, Base):
    __tablename__ = "ai_change_events"
    __table_args__ = (Index("ix_ai_change_event_tenant_created", "tenant_id", "created_at"),)
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    details_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
