from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class PerformanceRunModel(TimestampMixin, Base):
    __tablename__ = "performance_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", name="uq_performance_run_tenant_run"),
        Index("ix_performance_run_tenant_started", "tenant_id", "started_at"),
    )
    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    suite_name: Mapped[str] = mapped_column(String(120), nullable=False)
    candidate_version: Mapped[str] = mapped_column(String(160), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    config_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class PerformanceMetricModel(TimestampMixin, Base):
    __tablename__ = "performance_metrics"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "metric_key", name="uq_performance_metric_run_key"),
        Index("ix_performance_metric_tenant_run", "tenant_id", "run_id"),
    )
    metric_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    comparator: Mapped[str] = mapped_column(String(12), nullable=False, default="lte")
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ResilienceExperimentModel(TimestampMixin, Base):
    __tablename__ = "resilience_experiments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "experiment_id", name="uq_resilience_experiment_tenant_id"),
        Index("ix_resilience_experiment_tenant_started", "tenant_id", "started_at"),
    )
    experiment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_name: Mapped[str] = mapped_column(String(160), nullable=False)
    dependency: Mapped[str] = mapped_column(String(80), nullable=False)
    failure_mode: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    steady_state_before: Mapped[bool] = mapped_column(Boolean, nullable=False)
    steady_state_after: Mapped[bool] = mapped_column(Boolean, nullable=False)
    authorization_boundary_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_integrity_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recovery_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    experiment_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class CapacitySnapshotModel(TimestampMixin, Base):
    __tablename__ = "capacity_snapshots"
    __table_args__ = (Index("ix_capacity_snapshot_tenant_created", "tenant_id", "created_at"),)
    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    api_replicas: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_replicas: Mapped[int] = mapped_column(Integer, nullable=False)
    concurrent_users: Mapped[int] = mapped_column(Integer, nullable=False)
    sustained_rps: Mapped[float] = mapped_column(Float, nullable=False)
    sse_connections: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_events_per_second: Mapped[float] = mapped_column(Float, nullable=False)
    headroom_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    assumptions_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
