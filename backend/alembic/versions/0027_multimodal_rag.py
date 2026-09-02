"""multimodal RAG evidence packs and cross-modal verification telemetry

Revision ID: 0027_multimodal_rag
Revises: 0026_advanced_agentic_rag
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_multimodal_rag"
down_revision = "0026_advanced_agentic_rag"
branch_labels = None
depends_on = None

TABLES = (
    "multimodal_rag_runs",
    "multimodal_evidence_packs",
    "multimodal_rag_items",
    "multimodal_inconsistencies",
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
        "multimodal_rag_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(80)),
        sa.Column("intent", sa.String(60), nullable=False),
        sa.Column("requested_modalities", sa.JSON(), nullable=False),
        sa.Column("routed_modalities", sa.JSON(), nullable=False),
        sa.Column("required_modalities", sa.JSON(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("modality_coverage", sa.Float(), nullable=False),
        sa.Column("citation_coverage", sa.Float(), nullable=False),
        sa.Column("source_diversity", sa.Float(), nullable=False),
        sa.Column("inconsistency_count", sa.Integer(), nullable=False),
        sa.Column("knowledge_gap_count", sa.Integer(), nullable=False),
        sa.Column("answerability", sa.String(30), nullable=False),
        sa.Column("planner_version", sa.String(120), nullable=False),
        sa.Column("reranker_version", sa.String(120), nullable=False),
        sa.Column("verifier_version", sa.String(120), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_multimodal_rag_run_claim", "multimodal_rag_runs", ["tenant_id", "claim_id", "created_at"])
    op.create_index("ix_multimodal_rag_run_trace", "multimodal_rag_runs", ["tenant_id", "trace_id"])

    op.create_table(
        "multimodal_evidence_packs",
        sa.Column("pack_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("modalities", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("modality_coverage", sa.Float(), nullable=False),
        sa.Column("citation_coverage", sa.Float(), nullable=False),
        sa.Column("answerability", sa.String(30), nullable=False),
        sa.Column("pack_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_multimodal_pack_claim", "multimodal_evidence_packs", ["tenant_id", "claim_id", "created_at"])

    op.create_table(
        "multimodal_rag_items",
        sa.Column("item_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("multimodal_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(160), nullable=False),
        sa.Column("modality", sa.String(30), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False),
        sa.Column("metadata_summary", sa.JSON(), nullable=False),
        sa.Column("retrieval_sources", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_multimodal_item_run", "multimodal_rag_items", ["tenant_id", "run_id", "rank"])
    op.create_index("ix_multimodal_item_source", "multimodal_rag_items", ["tenant_id", "source_id", "source_version"])

    op.create_table(
        "multimodal_inconsistencies",
        sa.Column("inconsistency_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("multimodal_rag_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("multimodal_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("field", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("left_item_id", sa.String(160), nullable=False),
        sa.Column("right_item_id", sa.String(160), nullable=False),
        sa.Column("left_value_sha256", sa.String(64), nullable=False),
        sa.Column("right_value_sha256", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_multimodal_inconsistency_run", "multimodal_inconsistencies", ["tenant_id", "run_id", "created_at"])

    for table in TABLES:
        _rls(table)
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
