"""GitOps release engineering and deployment audit persistence.
Revision ID: 0022_release_engineering
Revises: 0021_security_privacy_devsecops
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_release_engineering"
down_revision = "0021_security_privacy_devsecops"
branch_labels = None
depends_on = None

TABLES = ("release_manifests", "deployment_records", "release_gate_results")


def _rls(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(
        f'CREATE POLICY {table}_tenant_isolation ON "{table}" '
        "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
    )


def upgrade() -> None:
    op.create_table(
        "release_manifests",
        sa.Column("manifest_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", sa.String(128), nullable=False),
        sa.Column("git_sha", sa.String(64), nullable=False),
        sa.Column("api_image_digest", sa.String(80), nullable=False),
        sa.Column("frontend_image_digest", sa.String(80), nullable=False),
        sa.Column("alembic_head", sa.String(128), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("sbom_sha256", sa.String(64), nullable=False),
        sa.Column("provenance_sha256", sa.String(64), nullable=False),
        sa.Column("gate_summary", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "release_id", name="uq_release_manifest_tenant_release"),
    )
    op.create_index("ix_release_manifest_tenant_created", "release_manifests", ["tenant_id", "created_at"])

    op.create_table(
        "deployment_records",
        sa.Column("deployment_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", sa.String(128), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("desired_state_sha", sa.String(64), nullable=False),
        sa.Column("argocd_application", sa.String(128), nullable=False),
        sa.Column("initiated_by", sa.String(128), nullable=False),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("rollback_release_id", sa.String(128)),
        sa.Column("rollback_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "deployment_id", name="uq_deployment_record_tenant_deployment"),
    )
    op.create_index("ix_deployment_tenant_environment_started", "deployment_records", ["tenant_id", "environment", "started_at"])

    op.create_table(
        "release_gate_results",
        sa.Column("gate_result_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", sa.String(128), nullable=False),
        sa.Column("gate_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "release_id", "gate_name", name="uq_release_gate_result"),
    )
    op.create_index("ix_release_gate_tenant_release", "release_gate_results", ["tenant_id", "release_id"])

    for table in TABLES:
        _rls(table)
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
