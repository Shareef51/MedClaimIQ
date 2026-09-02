from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TenantModel(TimestampMixin, Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("status IN ('active','suspended','disabled')", name="valid_status"),
        CheckConstraint(
            "tenant_type IN ('payer','provider','hospital','third_party_administrator','demo')",
            name="valid_type",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    tenant_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    data_region: Mapped[str] = mapped_column(String(32), nullable=False, default="local")

    memberships: Mapped[list["TenantMembershipModel"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    organizations: Mapped[list["OrganizationModel"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class OrganizationModel(TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "organization_type IN ('payer','provider','hospital','department','third_party_administrator')",
            name="valid_type",
        ),
        UniqueConstraint("tenant_id", "slug", name="slug_per_tenant"),
        Index("ix_organization_tenant_type", "tenant_id", "organization_type"),
    )

    organization_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_identifiers: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant: Mapped[TenantModel] = relationship(back_populates="organizations")


class UserAccountModel(TimestampMixin, Base):
    __tablename__ = "user_accounts"
    __table_args__ = (
        CheckConstraint("status IN ('invited','active','suspended','disabled')", name="valid_status"),
        UniqueConstraint("external_issuer", "external_subject", name="issuer_subject_identity"),
    )

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    external_issuer: Mapped[str] = mapped_column(
        String(512), nullable=False, default="https://identity.local.medclaimiq", index=True
    )
    external_subject: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="invited", index=True)

    memberships: Mapped[list["TenantMembershipModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="TenantMembershipModel.user_id",
    )


class TenantMembershipModel(TimestampMixin, Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="one_membership_per_user_tenant"),
        CheckConstraint(
            "role IN ('patient','provider','hospital_admin','claims_reviewer','finance_operator','finance_analyst','finance_approver','accounting_controller','auditor','tenant_admin','system_admin')",
            name="valid_role",
        ),
        CheckConstraint("status IN ('invited','active','suspended','disabled')", name="valid_status"),
        Index("ix_membership_tenant_role", "tenant_id", "role"),
    )

    membership_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="invited")
    patient_subject_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_organization_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    invited_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[TenantModel] = relationship(back_populates="memberships")
    user: Mapped[UserAccountModel] = relationship(
        back_populates="memberships", foreign_keys=[user_id]
    )


class ResourceGrantModel(TimestampMixin, Base):
    __tablename__ = "resource_grants"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('claim','evidence','hospital_record','audit_event','tenant_member','tenant_settings','tenant','system_health')",
            name="valid_resource_type",
        ),
        Index("ix_resource_grant_resource", "owner_tenant_id", "resource_type", "resource_id"),
        Index("ix_resource_grant_grantee", "grantee_tenant_id", "is_active"),
    )

    grant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    grantee_tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(160), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False
    )
