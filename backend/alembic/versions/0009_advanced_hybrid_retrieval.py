"""Add advanced hybrid retrieval telemetry persistence.

Revision ID: 0009_advanced_hybrid_retrieval
Revises: 0008_multi_rag_vector_foundation
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0009_advanced_hybrid_retrieval"
down_revision: str | None = "0008_multi_rag_vector_foundation"
branch_labels = None
depends_on = None

TABLES = ("rag_retrieval_runs", "rag_retrieval_candidates")


def _tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_tenant_isolation ON {table}
        USING (tenant_id = current_setting('app.current_tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"""
    )


def upgrade() -> None:
    op.create_table(
        "rag_retrieval_runs",
        sa.Column("retrieval_run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(30), nullable=False),
        sa.Column("requested_domains", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("planned_domains", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("query_variant_count", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("source_diversity", sa.Float(), nullable=False),
        sa.Column("no_evidence", sa.Boolean(), nullable=False),
        sa.Column("no_evidence_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("fallback_steps", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("planner_version", sa.String(120), nullable=False),
        sa.Column("reranker_version", sa.String(120), nullable=False),
        sa.Column("compression_applied", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("query_length >= 0 AND candidate_count >= 0 AND selected_count >= 0 AND latency_ms >= 0", name="ck_rag_retrieval_run_nonnegative"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1 AND coverage >= 0 AND coverage <= 1", name="ck_rag_retrieval_run_scores"),
    )
    for name, cols in (
        ("ix_rag_retrieval_runs_tenant_id", ["tenant_id"]),
        ("ix_rag_retrieval_runs_claim_id", ["claim_id"]),
        ("ix_rag_retrieval_run_claim", ["tenant_id", "claim_id", "created_at"]),
        ("ix_rag_retrieval_run_query_hash", ["tenant_id", "query_sha256"]),
    ):
        op.create_index(name, "rag_retrieval_runs", cols)

    op.create_table(
        "rag_retrieval_candidates",
        sa.Column("candidate_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("retrieval_run_id", sa.String(128), sa.ForeignKey("rag_retrieval_runs.retrieval_run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=True),
        sa.Column("final_rank", sa.Integer(), nullable=False),
        sa.Column("dense_score", sa.Float(), nullable=True),
        sa.Column("sparse_score", sa.Float(), nullable=True),
        sa.Column("fused_score", sa.Float(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retrieval_sources", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("metadata_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("final_rank >= 1", name="ck_rag_retrieval_candidate_rank"),
    )
    for name, cols in (
        ("ix_rag_retrieval_candidates_tenant_id", ["tenant_id"]),
        ("ix_rag_retrieval_candidates_claim_id", ["claim_id"]),
        ("ix_rag_retrieval_candidates_retrieval_run_id", ["retrieval_run_id"]),
        ("ix_rag_retrieval_candidate_run", ["tenant_id", "retrieval_run_id", "final_rank"]),
        ("ix_rag_retrieval_candidate_chunk", ["tenant_id", "chunk_id"]),
    ):
        op.create_index(name, "rag_retrieval_candidates", cols)

    for table in TABLES:
        _tenant_rls(table)

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_retrieval_telemetry_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'append-only retrieval telemetry';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_retrieval_telemetry_mutation()"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_retrieval_telemetry_mutation()")
