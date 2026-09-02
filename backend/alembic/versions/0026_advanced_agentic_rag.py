"""advanced agentic RAG planning, citation and gap telemetry

Revision ID: 0026_advanced_agentic_rag
Revises: 0025_knowledge_lifecycle_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_advanced_agentic_rag"
down_revision = "0025_knowledge_lifecycle_governance"
branch_labels = None
depends_on = None

TABLES = ("advanced_rag_runs", "advanced_rag_events")


def _rls(table: str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(
        f'CREATE POLICY {table}_tenant_isolation ON "{table}" '
        "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
    )


def upgrade():
    op.create_table(
        "advanced_rag_runs",
        sa.Column("advanced_run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("retrieval_run_id", sa.String(128), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(80)),
        sa.Column("query_intent", sa.String(50), nullable=False),
        sa.Column("routing_mode", sa.String(50), nullable=False),
        sa.Column("retrieval_strategy", sa.String(30), nullable=False),
        sa.Column("planner_version", sa.String(120), nullable=False),
        sa.Column("reranker_version", sa.String(120), nullable=False),
        sa.Column("rewrite_count", sa.Integer(), nullable=False),
        sa.Column("hyde_used", sa.Boolean(), nullable=False),
        sa.Column("model_assisted", sa.Boolean(), nullable=False),
        sa.Column("requested_domains", sa.JSON(), nullable=False),
        sa.Column("planned_domains", sa.JSON(), nullable=False),
        sa.Column("metadata_predicates", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("citation_coverage", sa.Float(), nullable=False),
        sa.Column("answerability", sa.String(30), nullable=False),
        sa.Column("knowledge_gap_count", sa.Integer(), nullable=False),
        sa.Column("rounds_executed", sa.Integer(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_advanced_rag_run_claim", "advanced_rag_runs", ["tenant_id", "claim_id", "created_at"])
    op.create_index("ix_advanced_rag_run_trace", "advanced_rag_runs", ["tenant_id", "trace_id"])
    op.create_index("ix_advanced_rag_run_query", "advanced_rag_runs", ["tenant_id", "query_sha256"])

    op.create_table(
        "advanced_rag_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("advanced_run_id", sa.String(128), sa.ForeignKey("advanced_rag_runs.advanced_run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_advanced_rag_event_run", "advanced_rag_events", ["tenant_id", "advanced_run_id", "created_at"])

    for table in TABLES:
        _rls(table)
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
