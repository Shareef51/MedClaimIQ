"""durable agent orchestration audit and human checkpoint tables

Revision ID: 0012_langgraph_agent_orchestration
Revises: 0011_rag_grounding_guardrails
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_langgraph_agent_orchestration"
down_revision = "0011_rag_grounding_guardrails"
branch_labels = None
depends_on = None

TABLES = (
    "agent_workflows", "agent_executions", "agent_findings",
    "agent_human_checkpoints", "agent_workflow_events",
)
APPEND_ONLY = ("agent_executions", "agent_findings", "agent_workflow_events")


def _tenant_rls(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
        USING (tenant_id = current_setting('app.current_tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))''')


def upgrade() -> None:
    op.create_table(
        "agent_workflows",
        sa.Column("workflow_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_pack_sha256", sa.String(64), nullable=False),
        sa.Column("guardrail_run_id", sa.String(128), sa.ForeignKey("rag_guardrail_runs.run_id", ondelete="SET NULL"), nullable=True),
        sa.Column("workflow_key", sa.String(160), nullable=False),
        sa.Column("thread_id", sa.String(160), nullable=False, unique=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("selected_agents", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("completed_agents", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("failed_agents", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "claim_id", "workflow_key", name="uq_agent_workflow_claim_key"),
    )
    op.create_index("ix_agent_workflow_claim", "agent_workflows", ["tenant_id", "claim_id", "created_at"])
    op.create_index("ix_agent_workflow_status", "agent_workflows", ["tenant_id", "status", "updated_at"])
    op.create_index("ix_agent_workflows_evidence_pack_id", "agent_workflows", ["evidence_pack_id"])

    op.create_table(
        "agent_executions",
        sa.Column("execution_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message_sha256", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "workflow_id", "agent_name", "attempt", name="uq_agent_execution_attempt"),
        sa.CheckConstraint("attempt >= 1", name="agent_execution_attempt_positive"),
    )
    op.create_index("ix_agent_execution_workflow", "agent_executions", ["tenant_id", "workflow_id", "created_at"])

    op.create_table(
        "agent_findings",
        sa.Column("finding_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_id", sa.String(128), sa.ForeignKey("agent_executions.execution_id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=False),
        sa.Column("summary_sha256", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_keys", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("risk_flags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="agent_finding_confidence_range"),
    )
    op.create_index("ix_agent_finding_workflow", "agent_findings", ["tenant_id", "workflow_id", "agent_name"])

    op.create_table(
        "agent_human_checkpoints",
        sa.Column("checkpoint_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("message_sha256", sa.String(64), nullable=False),
        sa.Column("required_permissions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(40), nullable=False, server_default="waiting"),
        sa.Column("resumed_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True),
        sa.Column("resume_action", sa.String(80), nullable=True),
        sa.Column("resume_comment_sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_checkpoint_workflow", "agent_human_checkpoints", ["tenant_id", "workflow_id", "created_at"])
    op.create_index("ix_agent_checkpoint_status", "agent_human_checkpoints", ["tenant_id", "status", "created_at"])

    op.create_table(
        "agent_workflow_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_type", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_agent_workflow_event_idempotency"),
        sa.CheckConstraint("sequence >= 1", name="agent_workflow_event_sequence_positive"),
    )
    op.create_index("ix_agent_workflow_event", "agent_workflow_events", ["tenant_id", "workflow_id", "sequence"])

    for table in TABLES:
        _tenant_rls(table)

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_agent_audit_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'immutable agent orchestration audit record';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in APPEND_ONLY:
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_agent_audit_mutation()")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_agent_audit_mutation()")
