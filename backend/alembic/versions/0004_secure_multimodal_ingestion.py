"""Add secure multimodal upload sessions, quarantine scans, and processing outbox.

Revision ID: 0004_secure_multimodal_ingestion
Revises: 0003_claim_evidence_domain
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0004_secure_multimodal_ingestion"
down_revision: str | None = "0003_claim_evidence_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence_artifacts", sa.Column("storage_etag", sa.String(160), nullable=True))
    op.add_column("evidence_artifacts", sa.Column("storage_version_id", sa.String(256), nullable=True))
    op.add_column(
        "evidence_artifacts",
        sa.Column("media_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.alter_column("evidence_artifacts", "media_metadata", server_default=None)
    op.add_column("evidence_artifacts", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "evidence_upload_sessions",
        sa.Column("upload_session_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiated_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bucket_name", sa.String(128), nullable=False),
        sa.Column("quarantine_object_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("accepted_object_key", sa.String(1024), nullable=True),
        sa.Column("client_filename_sha256", sa.String(64), nullable=False),
        sa.Column("client_extension", sa.String(16), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("declared_media_type", sa.String(160), nullable=False),
        sa.Column("detected_media_type", sa.String(160), nullable=True),
        sa.Column("media_kind", sa.String(30), nullable=False),
        sa.Column("expected_byte_size", sa.Integer(), nullable=False),
        sa.Column("expected_sha256", sa.String(64), nullable=True),
        sa.Column("actual_byte_size", sa.Integer(), nullable=True),
        sa.Column("actual_sha256", sa.String(64), nullable=True),
        sa.Column("storage_etag", sa.String(160), nullable=True),
        sa.Column("storage_version_id", sa.String(256), nullable=True),
        sa.Column("media_metadata", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("status_version", sa.Integer(), nullable=False),
        sa.Column("rejection_code", sa.String(80), nullable=True),
        sa.Column("rejection_detail", sa.String(500), nullable=True),
        sa.Column("evidence_id", sa.String(128), sa.ForeignKey("evidence_artifacts.evidence_id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("expected_byte_size > 0", name="ck_evidence_upload_sessions_positive_expected_size"),
        sa.CheckConstraint("actual_byte_size IS NULL OR actual_byte_size > 0", name="ck_evidence_upload_sessions_positive_actual_size"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_evidence_upload_sessions_idempotency_per_tenant"),
    )
    op.create_index("ix_evidence_upload_sessions_tenant_id", "evidence_upload_sessions", ["tenant_id"])
    op.create_index("ix_evidence_upload_sessions_claim_id", "evidence_upload_sessions", ["claim_id"])
    op.create_index("ix_evidence_upload_sessions_initiated_by_user_id", "evidence_upload_sessions", ["initiated_by_user_id"])
    op.create_index("ix_evidence_upload_sessions_evidence_id", "evidence_upload_sessions", ["evidence_id"])
    op.create_index("ix_upload_session_tenant_claim", "evidence_upload_sessions", ["tenant_id", "claim_id"])
    op.create_index("ix_upload_session_tenant_status", "evidence_upload_sessions", ["tenant_id", "status"])
    op.create_index("ix_upload_session_expires", "evidence_upload_sessions", ["tenant_id", "upload_expires_at"])

    op.create_table(
        "malware_scans",
        sa.Column("scan_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_session_id", sa.String(128), sa.ForeignKey("evidence_upload_sessions.upload_session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("scanner_name", sa.String(120), nullable=False),
        sa.Column("scanner_version", sa.String(80), nullable=True),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("signature_name", sa.String(240), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "upload_session_id", "attempt_number", name="uq_malware_scans_attempt_per_upload"),
    )
    op.create_index("ix_malware_scans_tenant_id", "malware_scans", ["tenant_id"])
    op.create_index("ix_malware_scans_upload_session_id", "malware_scans", ["upload_session_id"])
    op.create_index("ix_malware_scan_tenant_upload", "malware_scans", ["tenant_id", "upload_session_id"])
    op.create_index("ix_malware_scan_tenant_verdict", "malware_scans", ["tenant_id", "verdict"])

    op.create_table(
        "evidence_processing_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("aggregate_type", sa.String(60), nullable=False),
        sa.Column("aggregate_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_evidence_processing_events_idempotency_per_tenant"),
    )
    op.create_index("ix_evidence_processing_events_tenant_id", "evidence_processing_events", ["tenant_id"])
    op.create_index("ix_evidence_processing_events_claim_id", "evidence_processing_events", ["claim_id"])
    op.create_index("ix_evidence_processing_events_aggregate_id", "evidence_processing_events", ["aggregate_id"])
    op.create_index("ix_evidence_event_tenant_aggregate", "evidence_processing_events", ["tenant_id", "aggregate_id", "occurred_at"])
    op.create_index("ix_evidence_event_tenant_type", "evidence_processing_events", ["tenant_id", "event_type", "occurred_at"])

    op.create_table(
        "evidence_event_outbox",
        sa.Column("outbox_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(128), sa.ForeignKey("evidence_processing_events.event_id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(160), nullable=False),
        sa.Column("partition_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("last_error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "event_id", name="uq_evidence_event_outbox_one_outbox_row_per_event"),
    )
    op.create_index("ix_evidence_event_outbox_tenant_id", "evidence_event_outbox", ["tenant_id"])
    op.create_index("ix_evidence_event_outbox_event_id", "evidence_event_outbox", ["event_id"])
    op.create_index("ix_evidence_outbox_dispatch", "evidence_event_outbox", ["status", "available_at", "created_at"])
    op.create_index("ix_evidence_outbox_tenant_status", "evidence_event_outbox", ["tenant_id", "status"])

    for table in (
        "evidence_upload_sessions",
        "malware_scans",
        "evidence_processing_events",
        "evidence_event_outbox",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
        )

    # Scan records and domain events are evidence/provenance records and must never be rewritten.
    op.execute(
        "CREATE TRIGGER malware_scans_immutable BEFORE UPDATE OR DELETE ON malware_scans "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )
    op.execute(
        "CREATE TRIGGER evidence_processing_events_immutable BEFORE UPDATE OR DELETE ON evidence_processing_events "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS evidence_processing_events_immutable ON evidence_processing_events")
    op.execute("DROP TRIGGER IF EXISTS malware_scans_immutable ON malware_scans")
    for table in (
        "evidence_event_outbox",
        "evidence_processing_events",
        "malware_scans",
        "evidence_upload_sessions",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("evidence_event_outbox")
    op.drop_table("evidence_processing_events")
    op.drop_table("malware_scans")
    op.drop_table("evidence_upload_sessions")
    op.drop_column("evidence_artifacts", "verified_at")
    op.drop_column("evidence_artifacts", "media_metadata")
    op.drop_column("evidence_artifacts", "storage_version_id")
    op.drop_column("evidence_artifacts", "storage_etag")
