"""OIDC identity keys and revocable application sessions.

Revision ID: 0002_oidc_authentication_sessions
Revises: 0001_enterprise_tenancy
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0002_oidc_authentication_sessions"
down_revision: str | None = "0001_enterprise_tenancy"
branch_labels = None
depends_on = None


LOCAL_ISSUER = "https://identity.local.medclaimiq"


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column(
            "external_issuer",
            sa.String(512),
            nullable=False,
            server_default=LOCAL_ISSUER,
        ),
    )
    op.create_index("ix_user_accounts_external_issuer", "user_accounts", ["external_issuer"])
    op.drop_constraint("uq_user_accounts_external_subject", "user_accounts", type_="unique")
    op.create_unique_constraint(
        "issuer_subject_identity",
        "user_accounts",
        ["external_issuer", "external_subject"],
    )
    op.alter_column("user_accounts", "external_issuer", server_default=None)

    op.create_table(
        "authentication_sessions",
        sa.Column("session_id", sa.String(128), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("user_accounts.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(256), nullable=False),
        sa.Column("external_session_hash", sa.String(64), nullable=False),
        sa.Column("token_jti_hash", sa.String(64), nullable=True),
        sa.Column("client_fingerprint_hash", sa.String(64), nullable=True),
        sa.Column("authenticated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_by_user_id",
            sa.String(128),
            sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "issuer",
            "subject",
            "external_session_hash",
            name="external_session_per_tenant",
        ),
    )
    op.create_index("ix_authentication_sessions_tenant_id", "authentication_sessions", ["tenant_id"])
    op.create_index("ix_authentication_sessions_user_id", "authentication_sessions", ["user_id"])
    op.create_index(
        "ix_auth_session_user_tenant",
        "authentication_sessions",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_auth_session_active_lookup",
        "authentication_sessions",
        ["tenant_id", "expires_at", "revoked_at"],
    )

    op.execute("ALTER TABLE authentication_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE authentication_sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY authentication_sessions_tenant_isolation ON authentication_sessions "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS authentication_sessions_tenant_isolation ON authentication_sessions"
    )
    op.drop_table("authentication_sessions")
    op.drop_constraint("issuer_subject_identity", "user_accounts", type_="unique")
    op.create_unique_constraint(
        "uq_user_accounts_external_subject", "user_accounts", ["external_subject"]
    )
    op.drop_index("ix_user_accounts_external_issuer", table_name="user_accounts")
    op.drop_column("user_accounts", "external_issuer")
