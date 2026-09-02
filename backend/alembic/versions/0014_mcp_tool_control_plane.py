"""MCP tool gateway, approvals and immutable telemetry

Revision ID: 0014_mcp_tool_control_plane
Revises: 0013_specialist_agent_audit
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_mcp_tool_control_plane"
down_revision = "0013_specialist_agent_audit"
branch_labels = None
depends_on = None

TABLES = ("mcp_tool_invocations", "mcp_approval_requests", "mcp_tool_health_events")
IMMUTABLE_TABLES = ("mcp_tool_invocations", "mcp_tool_health_events")


def _tenant_rls(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
        USING (tenant_id = current_setting('app.current_tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))''')


def upgrade() -> None:
    op.create_table(
        "mcp_tool_invocations",
        sa.Column("invocation_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_type", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=True),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("tool_version", sa.String(40), nullable=False),
        sa.Column("risk_tier", sa.String(40), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("approval_id", sa.String(128), nullable=True),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("output_sha256", sa.String(64), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("sanitized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_sha256", sa.String(64), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_mcp_invocation_idempotency"),
    )
    op.create_index("ix_mcp_invocation_claim", "mcp_tool_invocations", ["tenant_id", "claim_id", "created_at"])
    op.create_index("ix_mcp_invocation_tool", "mcp_tool_invocations", ["tenant_id", "tool_name", "created_at"])
    op.create_index("ix_mcp_invocation_approval", "mcp_tool_invocations", ["approval_id"])

    op.create_table(
        "mcp_approval_requests",
        sa.Column("approval_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by_actor_type", sa.String(40), nullable=False),
        sa.Column("requested_by_actor_id", sa.String(128), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=True),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("tool_version", sa.String(40), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("decided_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True),
        sa.Column("decision_comment_sha256", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mcp_approval_claim", "mcp_approval_requests", ["tenant_id", "claim_id", "status", "created_at"])

    op.create_table(
        "mcp_tool_health_events",
        sa.Column("health_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("circuit_state", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mcp_health_tool", "mcp_tool_health_events", ["tenant_id", "tool_name", "occurred_at"])

    for table in TABLES:
        _tenant_rls(table)
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_mcp_audit_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'immutable MCP tool audit record';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in IMMUTABLE_TABLES:
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_mcp_audit_mutation()")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_mcp_audit_mutation()")
