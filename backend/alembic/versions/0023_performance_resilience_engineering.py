"""Performance, scalability and resilience engineering evidence persistence.
Revision ID: 0023_performance_resilience_engineering
Revises: 0022_release_engineering
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_performance_resilience_engineering"
down_revision = "0022_release_engineering"
branch_labels = None
depends_on = None

TABLES = ("performance_runs", "performance_metrics", "resilience_experiments", "capacity_snapshots")
IMMUTABLE = TABLES


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
        "performance_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("suite_name", sa.String(120), nullable=False),
        sa.Column("candidate_version", sa.String(160), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("config_sha256", sa.String(64), nullable=False),
        sa.Column("report_sha256", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "run_id", name="uq_performance_run_tenant_run"),
    )
    op.create_index("ix_performance_run_tenant_started", "performance_runs", ["tenant_id", "started_at"])

    op.create_table(
        "performance_metrics",
        sa.Column("metric_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), nullable=False),
        sa.Column("metric_key", sa.String(160), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("threshold_value", sa.Float()),
        sa.Column("baseline_value", sa.Float()),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("comparator", sa.String(12), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "run_id", "metric_key", name="uq_performance_metric_run_key"),
    )
    op.create_index("ix_performance_metric_tenant_run", "performance_metrics", ["tenant_id", "run_id"])

    op.create_table(
        "resilience_experiments",
        sa.Column("experiment_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_name", sa.String(160), nullable=False),
        sa.Column("dependency", sa.String(80), nullable=False),
        sa.Column("failure_mode", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("steady_state_before", sa.Boolean(), nullable=False),
        sa.Column("steady_state_after", sa.Boolean(), nullable=False),
        sa.Column("authorization_boundary_preserved", sa.Boolean(), nullable=False),
        sa.Column("data_integrity_preserved", sa.Boolean(), nullable=False),
        sa.Column("recovery_seconds", sa.Float()),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "experiment_id", name="uq_resilience_experiment_tenant_id"),
    )
    op.create_index("ix_resilience_experiment_tenant_started", "resilience_experiments", ["tenant_id", "started_at"])

    op.create_table(
        "capacity_snapshots",
        sa.Column("snapshot_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("api_replicas", sa.Integer(), nullable=False),
        sa.Column("worker_replicas", sa.Integer(), nullable=False),
        sa.Column("concurrent_users", sa.Integer(), nullable=False),
        sa.Column("sustained_rps", sa.Float(), nullable=False),
        sa.Column("sse_connections", sa.Integer(), nullable=False),
        sa.Column("worker_events_per_second", sa.Float(), nullable=False),
        sa.Column("headroom_fraction", sa.Float(), nullable=False),
        sa.Column("assumptions_sha256", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_capacity_snapshot_tenant_created", "capacity_snapshots", ["tenant_id", "created_at"])

    for table in TABLES:
        _rls(table)
    for table in IMMUTABLE:
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
