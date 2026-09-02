from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class ReleaseManifestModel(TimestampMixin, Base):
    __tablename__ = "release_manifests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "release_id", name="uq_release_manifest_tenant_release"),
        Index("ix_release_manifest_tenant_created", "tenant_id", "created_at"),
    )
    manifest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    api_image_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    frontend_image_digest: Mapped[str] = mapped_column(String(80), nullable=False)
    alembic_head: Mapped[str] = mapped_column(String(128), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sbom_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeploymentRecordModel(TimestampMixin, Base):
    __tablename__ = "deployment_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "deployment_id", name="uq_deployment_record_tenant_deployment"),
        Index("ix_deployment_tenant_environment_started", "tenant_id", "environment", "started_at"),
    )
    deployment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    desired_state_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    argocd_application: Mapped[str] = mapped_column(String(128), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rollback_release_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rollback_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deployment_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class ReleaseGateResultModel(TimestampMixin, Base):
    __tablename__ = "release_gate_results"
    __table_args__ = (
        UniqueConstraint("tenant_id", "release_id", "gate_name", name="uq_release_gate_result"),
        Index("ix_release_gate_tenant_release", "tenant_id", "release_id"),
    )
    gate_result_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False)
    gate_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
