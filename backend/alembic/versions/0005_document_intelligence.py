"""Add multimodal document intelligence runs, citation units, and extraction DLQ.

Revision ID: 0005_document_intelligence
Revises: 0004_secure_multimodal_ingestion
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision: str = "0005_document_intelligence"
down_revision: str | None = "0004_secure_multimodal_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_extraction_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.String(128), sa.ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_event_id", sa.String(128), sa.ForeignKey("evidence_processing_events.event_id", ondelete="SET NULL"), nullable=True),
        sa.Column("media_type", sa.String(160), nullable=False),
        sa.Column("pipeline_version", sa.String(80), nullable=False),
        sa.Column("parser_name", sa.String(120), nullable=True),
        sa.Column("parser_version", sa.String(80), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("aggregate_confidence", sa.Numeric(6,5), nullable=True),
        sa.Column("unit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("parser_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("derived_evidence_id", sa.String(128), sa.ForeignKey("evidence_artifacts.evidence_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_document_extraction_runs_idempotency_per_tenant"),
        sa.UniqueConstraint("tenant_id","evidence_id","pipeline_version","attempt_number",name="uq_document_extraction_runs_attempt_per_evidence_pipeline"),
    )
    for name, cols in (
        ("ix_document_extraction_runs_tenant_id", ["tenant_id"]),
        ("ix_document_extraction_runs_claim_id", ["claim_id"]),
        ("ix_document_extraction_runs_evidence_id", ["evidence_id"]),
        ("ix_extraction_run_tenant_claim", ["tenant_id","claim_id","status"]),
        ("ix_extraction_run_tenant_evidence", ["tenant_id","evidence_id","created_at"]),
    ): op.create_index(name,"document_extraction_runs",cols)

    op.create_table(
        "extraction_units",
        sa.Column("unit_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("run_id",sa.String(128),sa.ForeignKey("document_extraction_runs.run_id",ondelete="CASCADE"),nullable=False),
        sa.Column("source_evidence_id",sa.String(128),sa.ForeignKey("evidence_artifacts.evidence_id",ondelete="CASCADE"),nullable=False),
        sa.Column("unit_type",sa.String(40),nullable=False),
        sa.Column("sequence",sa.Integer(),nullable=False),
        sa.Column("text_content",sa.Text(),nullable=True),
        sa.Column("structured_data",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("confidence",sa.Numeric(6,5),nullable=False),
        sa.Column("page_number",sa.Integer(),nullable=True),
        sa.Column("start_ms",sa.Integer(),nullable=True),
        sa.Column("end_ms",sa.Integer(),nullable=True),
        sa.Column("bbox",sa.JSON(),nullable=True),
        sa.Column("source_locator",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("citation_anchor",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("content_sha256",sa.String(64),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","run_id","sequence",name="uq_extraction_units_sequence_per_run"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1",name="ck_extraction_units_confidence_range"),
        sa.CheckConstraint("page_number IS NULL OR page_number >= 1",name="ck_extraction_units_page_positive"),
        sa.CheckConstraint("(start_ms IS NULL AND end_ms IS NULL) OR (start_ms >= 0 AND end_ms >= start_ms)",name="ck_extraction_units_timestamp_range"),
    )
    for name, cols in (
        ("ix_extraction_units_tenant_id",["tenant_id"]),("ix_extraction_units_claim_id",["claim_id"]),("ix_extraction_units_run_id",["run_id"]),("ix_extraction_units_source_evidence_id",["source_evidence_id"]),
        ("ix_extraction_unit_tenant_claim",["tenant_id","claim_id","unit_type"]),("ix_extraction_unit_tenant_evidence",["tenant_id","source_evidence_id","sequence"]),
    ): op.create_index(name,"extraction_units",cols)

    op.create_table(
        "extraction_dead_letters",
        sa.Column("dead_letter_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("evidence_id",sa.String(128),sa.ForeignKey("evidence_artifacts.evidence_id",ondelete="CASCADE"),nullable=False),
        sa.Column("run_id",sa.String(128),sa.ForeignKey("document_extraction_runs.run_id",ondelete="CASCADE"),nullable=False),
        sa.Column("error_code",sa.String(80),nullable=False),
        sa.Column("error_detail",sa.Text(),nullable=False),
        sa.Column("replay_payload",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("trace_id",sa.String(128),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","run_id",name="uq_extraction_dead_letters_one_dead_letter_per_run"),
    )
    for name, cols in (("ix_extraction_dead_letters_tenant_id",["tenant_id"]),("ix_extraction_dead_letters_claim_id",["claim_id"]),("ix_extraction_dead_letters_evidence_id",["evidence_id"]),("ix_extraction_dead_letters_run_id",["run_id"]),("ix_extraction_dlq_tenant_claim",["tenant_id","claim_id","created_at"])): op.create_index(name,"extraction_dead_letters",cols)

    for table in ("document_extraction_runs","extraction_units","extraction_dead_letters"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_extraction_append_only_mutation() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'append-only extraction record cannot be updated or deleted'; END; $$ LANGUAGE plpgsql;
    """)
    for table in ("extraction_units","extraction_dead_letters"):
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_extraction_append_only_mutation()")


def downgrade() -> None:
    for table in ("extraction_units","extraction_dead_letters"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.drop_table("extraction_dead_letters")
    op.drop_table("extraction_units")
    op.drop_table("document_extraction_runs")
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_extraction_append_only_mutation()")
