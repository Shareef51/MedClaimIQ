"""specialist agent model and evidence-tool audit

Revision ID: 0013_specialist_agent_audit
Revises: 0012_langgraph_agent_orchestration
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_specialist_agent_audit"
down_revision = "0012_langgraph_agent_orchestration"
branch_labels = None
depends_on = None

TABLES = ("agent_model_invocations", "agent_tool_audits")


def _tenant_rls(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
        USING (tenant_id = current_setting('app.current_tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))''')


def upgrade() -> None:
    op.create_table(
        "agent_model_invocations",
        sa.Column("invocation_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("evidence_pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("prompt_key", sa.String(160), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("prompt_sha256", sa.String(64), nullable=False),
        sa.Column("input_context_sha256", sa.String(64), nullable=False),
        sa.Column("output_sha256", sa.String(64), nullable=False),
        sa.Column("provider_response_id", sa.String(160), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "workflow_id", "agent_name", "attempt", name="uq_agent_model_invocation_attempt"),
    )
    op.create_index("ix_agent_model_invocation_workflow", "agent_model_invocations", ["tenant_id", "workflow_id", "created_at"])

    op.create_table(
        "agent_tool_audits",
        sa.Column("audit_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(128), sa.ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False),
        sa.Column("invocation_id", sa.String(128), sa.ForeignKey("agent_model_invocations.invocation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(80), nullable=False),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("result_sha256", sa.String(64), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_tool_audit_workflow", "agent_tool_audits", ["tenant_id", "workflow_id", "agent_name", "created_at"])

    for table in TABLES:
        _tenant_rls(table)
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_specialist_agent_audit_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'immutable specialist agent audit record';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_specialist_agent_audit_mutation()")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_specialist_agent_audit_mutation()")
