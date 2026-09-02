"""Production SLA, timer, deadline and escalation engine.

Revision ID: 0016_sla_deadline_engine
Revises: 0015_realtime_event_backbone
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_sla_deadline_engine"
down_revision = "0015_realtime_event_backbone"
branch_labels = None
depends_on = None

TABLES = (
    "sla_policies", "sla_calendar_holidays", "sla_timers", "sla_timer_events",
    "sla_review_queue_entries", "sla_worker_failures",
)
IMMUTABLE = ("sla_timer_events", "sla_worker_failures")


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
        "sla_policies",
        sa.Column("policy_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_key", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("calendar_definition", sa.JSON(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "policy_key", "version", name="uq_sla_policy_version"),
    )
    op.create_index("ix_sla_policy_active", "sla_policies", ["tenant_id", "is_active", "effective_from"])

    op.create_table(
        "sla_calendar_holidays",
        sa.Column("holiday_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("calendar_key", sa.String(120), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "calendar_key", "holiday_date", name="uq_sla_calendar_holiday"),
    )
    op.create_index("ix_sla_holiday_calendar", "sla_calendar_holidays", ["tenant_id", "calendar_key", "holiday_date"])

    op.create_table(
        "sla_timers",
        sa.Column("timer_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_id", sa.String(128), sa.ForeignKey("sla_policies.policy_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("timer_type", sa.String(80), nullable=False),
        sa.Column("clock_mode", sa.String(30), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warning_schedule", sa.JSON(), nullable=False),
        sa.Column("next_warning_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_action_at", sa.DateTime(timezone=True)),
        sa.Column("source_event_id", sa.String(128)),
        sa.Column("source_event_type", sa.String(140)),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("breached_at", sa.DateTime(timezone=True)),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(100)),
        sa.Column("last_error_sha256", sa.String(64)),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_sla_timer_idempotency"),
    )
    op.create_index("ix_sla_timer_due", "sla_timers", ["tenant_id", "status", "next_action_at"])
    op.create_index("ix_sla_timer_claim", "sla_timers", ["tenant_id", "claim_id", "status", "due_at"])
    op.create_index("ix_sla_timer_type", "sla_timers", ["tenant_id", "timer_type", "status"])

    op.create_table(
        "sla_timer_events",
        sa.Column("sla_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timer_id", sa.String(128), sa.ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("timer_type", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_sla_timer_event_idempotency"),
    )
    op.create_index("ix_sla_event_claim", "sla_timer_events", ["tenant_id", "claim_id", "occurred_at"])
    op.create_index("ix_sla_event_timer", "sla_timer_events", ["tenant_id", "timer_id", "occurred_at"])

    op.create_table(
        "sla_review_queue_entries",
        sa.Column("queue_entry_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timer_id", sa.String(128), sa.ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False),
        sa.Column("escalation_level", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("assigned_reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL")),
        sa.Column("mcp_approval_id", sa.String(128), sa.ForeignKey("mcp_approval_requests.approval_id", ondelete="SET NULL")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "timer_id", "escalation_level", name="uq_sla_review_queue_timer_level"),
    )
    op.create_index("ix_sla_review_queue", "sla_review_queue_entries", ["tenant_id", "status", "priority", "created_at"])
    op.create_index("ix_sla_review_claim", "sla_review_queue_entries", ["tenant_id", "claim_id", "status"])

    op.create_table(
        "sla_worker_failures",
        sa.Column("failure_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timer_id", sa.String(128), sa.ForeignKey("sla_timers.timer_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=False),
        sa.Column("error_sha256", sa.String(64), nullable=False),
        sa.Column("retry_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "timer_id", "attempt", name="uq_sla_worker_failure_attempt"),
    )
    op.create_index("ix_sla_worker_failure", "sla_worker_failures", ["tenant_id", "created_at"])

    for table in TABLES:
        _rls(table)
    for table in IMMUTABLE:
        op.execute(
            f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" '
            'FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()'
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
