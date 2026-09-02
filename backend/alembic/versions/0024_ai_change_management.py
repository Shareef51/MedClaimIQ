"""AI configuration registry, experiments and controlled change management.
Revision ID: 0024_ai_change_management
Revises: 0023_performance_resilience_engineering
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_ai_change_management"
down_revision = "0023_performance_resilience_engineering"
branch_labels = None
depends_on = None

TABLES = (
    "ai_configuration_snapshots", "ai_environment_assignments", "ai_configuration_promotions",
    "ai_experiments", "ai_experiment_assignments", "ai_experiment_observations",
    "ai_configuration_drift_events", "ai_change_events",
)
IMMUTABLE = (
    "ai_configuration_snapshots", "ai_experiment_assignments", "ai_experiment_observations",
    "ai_configuration_drift_events", "ai_change_events",
)


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
        "ai_configuration_snapshots",
        sa.Column("snapshot_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("config_key", sa.String(180), nullable=False), sa.Column("version", sa.String(80), nullable=False),
        sa.Column("configuration_type", sa.String(24), nullable=False), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False), sa.Column("parent_snapshot_id", sa.String(128)),
        sa.Column("evaluation_baseline_id", sa.String(128)), sa.Column("evaluation_run_id", sa.String(128)),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "config_key", "version", name="uq_ai_config_snapshot_version"),
    )
    op.create_index("ix_ai_config_snapshot_tenant_key_created", "ai_configuration_snapshots", ["tenant_id", "config_key", "created_at"])

    op.create_table(
        "ai_environment_assignments",
        sa.Column("assignment_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False), sa.Column("config_key", sa.String(180), nullable=False),
        sa.Column("snapshot_id", sa.String(128), sa.ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False),
        sa.Column("assignment_version", sa.Integer(), nullable=False), sa.Column("source", sa.String(32), nullable=False),
        sa.Column("activated_by", sa.String(128), nullable=False), sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "environment", "config_key", name="uq_ai_environment_assignment"),
    )
    op.create_index("ix_ai_assignment_tenant_env", "ai_environment_assignments", ["tenant_id", "environment"])

    op.create_table(
        "ai_configuration_promotions",
        sa.Column("promotion_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_id", sa.String(128), sa.ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False),
        sa.Column("config_key", sa.String(180), nullable=False), sa.Column("target_environment", sa.String(32), nullable=False),
        sa.Column("risk", sa.String(20), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("requested_by", sa.String(128), nullable=False), sa.Column("approved_by", sa.String(128)),
        sa.Column("approval_reason", sa.String(1000)), sa.Column("evaluation_run_id", sa.String(128)),
        sa.Column("evaluation_decision", sa.String(20)), sa.Column("previous_snapshot_id", sa.String(128)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_promotion_tenant_created", "ai_configuration_promotions", ["tenant_id", "created_at"])

    op.create_table(
        "ai_experiments",
        sa.Column("experiment_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_key", sa.String(160), nullable=False), sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("champion_snapshot_id", sa.String(128), sa.ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False),
        sa.Column("challenger_snapshot_id", sa.String(128), sa.ForeignKey("ai_configuration_snapshots.snapshot_id"), nullable=False),
        sa.Column("challenger_basis_points", sa.Integer(), nullable=False), sa.Column("shadow_only", sa.Boolean(), nullable=False),
        sa.Column("evaluation_baseline_id", sa.String(128)), sa.Column("guardrails", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "experiment_key", name="uq_ai_experiment_key"),
    )

    op.create_table(
        "ai_experiment_assignments",
        sa.Column("assignment_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_id", sa.String(128), sa.ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_sha256", sa.String(64), nullable=False), sa.Column("bucket", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(24), nullable=False), sa.Column("snapshot_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "experiment_id", "subject_sha256", name="uq_ai_experiment_subject"),
    )
    op.create_index("ix_ai_experiment_assignment", "ai_experiment_assignments", ["tenant_id", "experiment_id"])

    op.create_table(
        "ai_experiment_observations",
        sa.Column("observation_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_id", sa.String(128), sa.ForeignKey("ai_experiments.experiment_id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.String(128)), sa.Column("variant", sa.String(24), nullable=False),
        sa.Column("quality_score", sa.Float()), sa.Column("latency_ms", sa.Float()), sa.Column("cost_usd", sa.Float()),
        sa.Column("evaluation_run_id", sa.String(128)), sa.Column("trace_id", sa.String(64)),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_experiment_observation", "ai_experiment_observations", ["tenant_id", "experiment_id", "created_at"])

    op.create_table(
        "ai_configuration_drift_events",
        sa.Column("drift_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False), sa.Column("config_key", sa.String(180), nullable=False),
        sa.Column("expected_snapshot_id", sa.String(128), nullable=False), sa.Column("observed_sha256", sa.String(64), nullable=False),
        sa.Column("expected_sha256", sa.String(64), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("detected_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_drift_tenant_detected", "ai_configuration_drift_events", ["tenant_id", "created_at"])

    op.create_table(
        "ai_change_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False), sa.Column("actor_user_id", sa.String(128), nullable=False),
        sa.Column("subject_type", sa.String(40), nullable=False), sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False), sa.Column("details_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_change_event_tenant_created", "ai_change_events", ["tenant_id", "created_at"])

    for table in TABLES:
        _rls(table)
    for table in IMMUTABLE:
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
