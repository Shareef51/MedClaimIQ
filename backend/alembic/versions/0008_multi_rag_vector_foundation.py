"""Add production multi-RAG chunk/index persistence.

Revision ID: 0008_multi_rag_vector_foundation
Revises: 0007_unified_evidence_graph
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0008_multi_rag_vector_foundation"
down_revision: str | None = "0007_unified_evidence_graph"
branch_labels = None
depends_on = None

TABLES = ("rag_chunks", "rag_index_jobs", "rag_index_records", "rag_index_dead_letters")


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
        "rag_chunks",
        sa.Column("chunk_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("parent_chunk_id", sa.String(128), sa.ForeignKey("rag_chunks.chunk_id", ondelete="CASCADE"), nullable=True),
        sa.Column("chunk_kind", sa.String(30), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("chunk_fingerprint", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "chunk_fingerprint", name="uq_rag_chunk_fingerprint"),
        sa.CheckConstraint("token_count >= 0", name="ck_rag_chunk_token_count"),
    )
    for name, cols in (
        ("ix_rag_chunks_tenant_id", ["tenant_id"]),
        ("ix_rag_chunks_claim_id", ["claim_id"]),
        ("ix_rag_chunks_patient_subject_id", ["patient_subject_id"]),
        ("ix_rag_chunks_domain", ["domain"]),
        ("ix_rag_chunks_parent_chunk_id", ["parent_chunk_id"]),
        ("ix_rag_chunk_claim_domain", ["tenant_id", "claim_id", "domain", "source_id"]),
        ("ix_rag_chunk_source_version", ["tenant_id", "source_type", "source_id", "source_version"]),
        ("ix_rag_chunk_parent", ["tenant_id", "parent_chunk_id"]),
    ):
        op.create_index(name, "rag_chunks", cols)

    op.create_table(
        "rag_index_jobs",
        sa.Column("job_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_rag_index_job_idempotency"),
        sa.CheckConstraint("attempt_number >= 0 AND max_attempts >= 1", name="ck_rag_index_attempts"),
    )
    for name, cols in (
        ("ix_rag_index_jobs_tenant_id", ["tenant_id"]),
        ("ix_rag_index_jobs_claim_id", ["claim_id"]),
        ("ix_rag_index_job_claim_status", ["tenant_id", "claim_id", "status"]),
        ("ix_rag_index_job_source", ["tenant_id", "source_type", "source_id", "source_version"]),
    ):
        op.create_index(name, "rag_index_jobs", cols)

    op.create_table(
        "rag_index_records",
        sa.Column("index_record_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(128), sa.ForeignKey("rag_chunks.chunk_id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("collection_name", sa.String(160), nullable=False),
        sa.Column("point_id", sa.String(128), nullable=False),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_input_sha256", sa.String(64), nullable=False),
        sa.Column("index_version", sa.String(80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "chunk_id", "embedding_model", "embedding_dimensions", "index_version", name="uq_rag_index_projection"),
        sa.CheckConstraint("embedding_dimensions > 0", name="ck_rag_embedding_dimensions"),
    )
    for name, cols in (
        ("ix_rag_index_records_tenant_id", ["tenant_id"]),
        ("ix_rag_index_records_claim_id", ["claim_id"]),
        ("ix_rag_index_records_chunk_id", ["chunk_id"]),
        ("ix_rag_index_record_claim", ["tenant_id", "claim_id", "domain", "active"]),
        ("ix_rag_index_record_source", ["tenant_id", "source_id", "source_version", "active"]),
    ):
        op.create_index(name, "rag_index_records", cols)

    op.create_table(
        "rag_index_dead_letters",
        sa.Column("dead_letter_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.String(128), sa.ForeignKey("rag_index_jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=False),
        sa.Column("replay_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "job_id", name="uq_rag_index_dead_letter_job"),
    )
    for name, cols in (
        ("ix_rag_index_dead_letters_tenant_id", ["tenant_id"]),
        ("ix_rag_index_dead_letters_claim_id", ["claim_id"]),
        ("ix_rag_index_dead_letters_job_id", ["job_id"]),
        ("ix_rag_index_dlq_claim", ["tenant_id", "claim_id", "created_at"]),
    ):
        op.create_index(name, "rag_index_dead_letters", cols)

    for table in TABLES:
        _tenant_rls(table)

    # Chunk text and projection history are immutable; active flags may change only through controlled
    # version/delete workflows. DLQ records are forensic and append-only.
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_rag_dlq_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'append-only RAG dead-letter history';
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER rag_index_dead_letters_append_only BEFORE UPDATE OR DELETE ON rag_index_dead_letters FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_rag_dlq_mutation()")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_rag_dlq_mutation()")
