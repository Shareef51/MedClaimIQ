from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class DataRetentionPolicyModel(TimestampMixin, Base):
    __tablename__ = "data_retention_policies"
    __table_args__ = (UniqueConstraint("tenant_id","policy_key","version",name="uq_retention_policy_version"),Index("ix_retention_tenant_active","tenant_id","active"))
    policy_id: Mapped[str] = mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    policy_key: Mapped[str] = mapped_column(String(120),nullable=False)
    version: Mapped[str] = mapped_column(String(40),nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80),nullable=False)
    classification: Mapped[str] = mapped_column(String(40),nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer,nullable=False)
    disposition: Mapped[str] = mapped_column(String(40),nullable=False,default="review_then_delete")
    active: Mapped[bool] = mapped_column(Boolean,nullable=False,default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(128),nullable=False)

class DataDispositionRequestModel(TimestampMixin, Base):
    __tablename__ = "data_disposition_requests"
    __table_args__ = (Index("ix_disposition_tenant_status","tenant_id","status"),UniqueConstraint("tenant_id","idempotency_key",name="uq_disposition_idem"))
    request_id: Mapped[str] = mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("data_retention_policies.policy_id",ondelete="RESTRICT"),nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80),nullable=False)
    resource_id: Mapped[str] = mapped_column(String(160),nullable=False)
    classification: Mapped[str] = mapped_column(String(40),nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128),nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(30),nullable=False,default="pending_approval")
    dry_run: Mapped[bool] = mapped_column(Boolean,nullable=False,default=True)
    idempotency_key: Mapped[str] = mapped_column(String(160),nullable=False)
    reason: Mapped[str] = mapped_column(Text,nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class AuditExportManifestModel(TimestampMixin, Base):
    __tablename__ = "audit_export_manifests"
    __table_args__ = (Index("ix_audit_export_tenant_created","tenant_id","created_at"),)
    export_id: Mapped[str] = mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    requested_by: Mapped[str] = mapped_column(String(128),nullable=False)
    from_time: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    to_time: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    record_count: Mapped[int] = mapped_column(Integer,nullable=False)
    root_sha256: Mapped[str] = mapped_column(String(64),nullable=False)
    signature_hmac_sha256: Mapped[str] = mapped_column(String(64),nullable=False)
    export_object_key: Mapped[str | None] = mapped_column(String(512))
    classification: Mapped[str] = mapped_column(String(40),nullable=False,default="confidential")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class SecurityReadinessRunModel(TimestampMixin, Base):
    __tablename__ = "security_readiness_runs"
    __table_args__ = (Index("ix_security_readiness_tenant_created","tenant_id","created_at"),)
    run_id: Mapped[str] = mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    candidate_version: Mapped[str] = mapped_column(String(160),nullable=False)
    decision: Mapped[str] = mapped_column(String(20),nullable=False)
    critical_findings: Mapped[int] = mapped_column(Integer,nullable=False,default=0)
    high_findings: Mapped[int] = mapped_column(Integer,nullable=False,default=0)
    control_pass_rate: Mapped[str] = mapped_column(String(20),nullable=False)
    report_sha256: Mapped[str] = mapped_column(String(64),nullable=False)
    controls_version: Mapped[str] = mapped_column(String(80),nullable=False)
    details: Mapped[dict] = mapped_column(JSON,nullable=False,default=dict)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)


class EncryptionKeyReferenceModel(TimestampMixin, Base):
    __tablename__ = "encryption_key_references"
    __table_args__ = (Index("ix_keyref_tenant_status","tenant_id","status"),UniqueConstraint("tenant_id","purpose","external_key_id",name="uq_keyref_external"))
    key_ref_id: Mapped[str] = mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    provider: Mapped[str] = mapped_column(String(40),nullable=False)
    purpose: Mapped[str] = mapped_column(String(80),nullable=False)
    external_key_id: Mapped[str] = mapped_column(String(512),nullable=False)
    status: Mapped[str] = mapped_column(String(20),nullable=False,default="active")
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    rotate_after: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
