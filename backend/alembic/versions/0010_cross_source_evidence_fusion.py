"""Add immutable cross-source evidence-pack persistence.

Revision ID: 0010_cross_source_evidence_fusion
Revises: 0009_advanced_hybrid_retrieval
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0010_cross_source_evidence_fusion"
down_revision: str | None = "0009_advanced_hybrid_retrieval"
branch_labels = None
depends_on = None

TABLES = ("rag_evidence_packs", "rag_evidence_pack_items", "rag_evidence_pack_contradictions")


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
        "rag_evidence_packs",
        sa.Column("pack_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("planner_version", sa.String(120), nullable=False),
        sa.Column("requested_retrievers", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("executed_retrievers", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("contradiction_count", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("source_diversity", sa.Float(), nullable=False),
        sa.Column("no_evidence", sa.Boolean(), nullable=False),
        sa.Column("unresolved_material_contradictions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessment_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("query_length >= 0 AND evidence_count >= 0 AND contradiction_count >= 0", name="evidence_pack_nonnegative"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1 AND coverage >= 0 AND coverage <= 1 AND source_diversity >= 0 AND source_diversity <= 1", name="evidence_pack_score_range"),
    )
    op.create_index("ix_rag_evidence_packs_tenant_id", "rag_evidence_packs", ["tenant_id"])
    op.create_index("ix_rag_evidence_packs_claim_id", "rag_evidence_packs", ["claim_id"])
    op.create_index("ix_rag_evidence_pack_claim", "rag_evidence_packs", ["tenant_id", "claim_id", "created_at"])
    op.create_index("ix_rag_evidence_pack_query", "rag_evidence_packs", ["tenant_id", "query_sha256"])

    op.create_table(
        "rag_evidence_pack_items",
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_key", sa.String(128), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("retriever", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("metadata_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "pack_id", "evidence_key", name="evidence_once_per_pack"),
        sa.CheckConstraint("rank >= 1 AND authority_rank >= 0 AND authority_rank <= 100 AND confidence >= 0 AND confidence <= 1", name="evidence_pack_item_range"),
    )
    for name, cols in (
        ("ix_rag_evidence_pack_items_tenant_id", ["tenant_id"]), ("ix_rag_evidence_pack_items_claim_id", ["claim_id"]),
        ("ix_rag_evidence_pack_items_pack_id", ["pack_id"]), ("ix_rag_evidence_pack_item_pack", ["tenant_id", "pack_id", "rank"]),
    ):
        op.create_index(name, "rag_evidence_pack_items", cols)

    op.create_table(
        "rag_evidence_pack_contradictions",
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("contradiction_id", sa.String(128), nullable=False),
        sa.Column("field_name", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "pack_id", "contradiction_id", name="contradiction_once_per_pack"),
    )
    for name, cols in (
        ("ix_rag_evidence_pack_contradictions_tenant_id", ["tenant_id"]),
        ("ix_rag_evidence_pack_contradictions_claim_id", ["claim_id"]),
        ("ix_rag_evidence_pack_contradictions_pack_id", ["pack_id"]),
        ("ix_rag_evidence_pack_contradiction", ["tenant_id", "pack_id", "severity"]),
    ):
        op.create_index(name, "rag_evidence_pack_contradictions", cols)

    for table in TABLES:
        _tenant_rls(table)

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_evidence_pack_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'immutable evidence pack snapshot';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_evidence_pack_mutation()"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_evidence_pack_mutation()")
