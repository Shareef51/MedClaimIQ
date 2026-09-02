"""Persist enterprise tenants, organizations, memberships, and resource grants.

Revision ID: 0001_enterprise_tenancy
Revises: None
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_enterprise_tenancy"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("tenant_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("data_region", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tenant_type IN ('payer','provider','hospital','third_party_administrator','demo')",
            name="ck_tenants_valid_type",
        ),
        sa.CheckConstraint(
            "status IN ('active','suspended','disabled')", name="ck_tenants_valid_status"
        ),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_status", "tenants", ["status"])

    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(180), nullable=False),
        sa.Column("organization_type", sa.String(40), nullable=False),
        sa.Column("external_identifiers", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "organization_type IN ('payer','provider','hospital','department','third_party_administrator')",
            name="ck_organizations_valid_type",
        ),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_organizations_slug_per_tenant"),
    )
    op.create_index("ix_organizations_tenant_id", "organizations", ["tenant_id"])
    op.create_index("ix_organization_tenant_type", "organizations", ["tenant_id", "organization_type"])

    op.create_table(
        "user_accounts",
        sa.Column("user_id", sa.String(128), primary_key=True),
        sa.Column("external_subject", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('invited','active','suspended','disabled')",
            name="ck_user_accounts_valid_status",
        ),
        sa.UniqueConstraint("external_subject", name="uq_user_accounts_external_subject"),
    )
    op.create_index("ix_user_accounts_external_subject", "user_accounts", ["external_subject"])
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"])
    op.create_index("ix_user_accounts_status", "user_accounts", ["status"])

    op.create_table(
        "tenant_memberships",
        sa.Column("membership_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=True),
        sa.Column("provider_organization_id", sa.String(128), nullable=True),
        sa.Column("invited_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('patient','provider','hospital_admin','claims_reviewer','auditor','tenant_admin','system_admin')",
            name="ck_tenant_memberships_valid_role",
        ),
        sa.CheckConstraint(
            "status IN ('invited','active','suspended','disabled')",
            name="ck_tenant_memberships_valid_status",
        ),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_one_membership_per_user_tenant"),
    )
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])
    op.create_index("ix_tenant_memberships_organization_id", "tenant_memberships", ["organization_id"])
    op.create_index("ix_tenant_memberships_patient_subject_id", "tenant_memberships", ["patient_subject_id"])
    op.create_index("ix_tenant_memberships_provider_organization_id", "tenant_memberships", ["provider_organization_id"])
    op.create_index("ix_membership_tenant_role", "tenant_memberships", ["tenant_id", "role"])

    op.create_table(
        "resource_grants",
        sa.Column("grant_id", sa.String(128), primary_key=True),
        sa.Column("owner_tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("grantee_tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(160), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.Column("created_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("owner_tenant_id <> grantee_tenant_id", name="ck_resource_grants_cross_tenant_only"),
        sa.CheckConstraint(
            "resource_type IN ('claim','evidence','hospital_record','audit_event','tenant_member','tenant_settings','tenant','system_health')",
            name="ck_resource_grants_valid_resource_type",
        ),
    )
    op.create_index("ix_resource_grants_owner_tenant_id", "resource_grants", ["owner_tenant_id"])
    op.create_index("ix_resource_grants_grantee_tenant_id", "resource_grants", ["grantee_tenant_id"])
    op.create_index("ix_resource_grant_resource", "resource_grants", ["owner_tenant_id", "resource_type", "resource_id"])
    op.create_index("ix_resource_grant_grantee", "resource_grants", ["grantee_tenant_id", "is_active"])

    # Defense-in-depth: application queries remain tenant-filtered; PostgreSQL RLS
    # independently denies rows outside the transaction-local tenant context.
    for table in ("organizations", "tenant_memberships"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
        )

    op.execute("ALTER TABLE resource_grants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE resource_grants FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY resource_grants_read ON resource_grants FOR SELECT "
        "USING (owner_tenant_id = current_setting('app.current_tenant_id', true) "
        "OR grantee_tenant_id = current_setting('app.current_tenant_id', true))"
    )
    op.execute(
        "CREATE POLICY resource_grants_owner_write ON resource_grants "
        "FOR ALL USING (owner_tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (owner_tenant_id = current_setting('app.current_tenant_id', true))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS resource_grants_owner_write ON resource_grants")
    op.execute("DROP POLICY IF EXISTS resource_grants_read ON resource_grants")
    for table in ("tenant_memberships", "organizations"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("resource_grants")
    op.drop_table("tenant_memberships")
    op.drop_table("user_accounts")
    op.drop_table("organizations")
    op.drop_table("tenants")
