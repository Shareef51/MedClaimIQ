"""knowledge lifecycle, RAG content governance and continuous reindexing

Revision ID: 0025_knowledge_lifecycle_governance
Revises: 0024_ai_change_management
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_knowledge_lifecycle_governance"
down_revision = "0024_ai_change_management"
branch_labels = None
depends_on = None

TABLES = (
    "knowledge_sources", "knowledge_documents", "knowledge_document_versions", "knowledge_quality_runs",
    "knowledge_reindex_jobs", "knowledge_index_migrations", "knowledge_retrieval_drift_events",
    "knowledge_releases", "knowledge_release_items", "knowledge_governance_events",
)
IMMUTABLE = (
    "knowledge_quality_runs", "knowledge_retrieval_drift_events",
    "knowledge_release_items", "knowledge_governance_events",
)


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


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
        "knowledge_sources",
        sa.Column("source_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(180), nullable=False), sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False), sa.Column("owner_principal_id", sa.String(128), nullable=False),
        sa.Column("owner_team", sa.String(128)), sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("onboarding_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "source_key", name="uq_knowledge_source_tenant_key"),
    )
    op.create_index("ix_knowledge_source_tenant_status", "knowledge_sources", ["tenant_id", "status"])

    op.create_table(
        "knowledge_documents",
        sa.Column("document_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(128), sa.ForeignKey("knowledge_sources.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_key", sa.String(220), nullable=False), sa.Column("title", sa.String(300), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False), sa.Column("source_locator", sa.String(1000)),
        sa.Column("metadata", sa.JSON(), nullable=False), sa.Column("created_by", sa.String(128), nullable=False), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "source_id", "document_key", name="uq_knowledge_document_source_key"),
    )
    op.create_index("ix_knowledge_document_source", "knowledge_documents", ["tenant_id", "source_id"])

    op.create_table(
        "knowledge_document_versions",
        sa.Column("version_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(128), sa.ForeignKey("knowledge_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(100), nullable=False), sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content_locator", sa.String(1000)), sa.Column("rag_source_id", sa.String(256), nullable=False),
        sa.Column("rag_source_version", sa.String(128), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True)), sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.JSON(), nullable=False), sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("submitted_by", sa.String(128)), sa.Column("approved_by", sa.String(128)),
        sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "document_id", "version", name="uq_knowledge_document_version"),
    )
    op.create_index("ix_knowledge_version_document_status", "knowledge_document_versions", ["tenant_id", "document_id", "status"])
    op.create_index("ix_knowledge_version_source_ref", "knowledge_document_versions", ["tenant_id", "rag_source_id", "rag_source_version"])

    op.create_table(
        "knowledge_quality_runs",
        sa.Column("quality_run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.String(128), sa.ForeignKey("knowledge_document_versions.version_id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False), sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("citation_coverage", sa.Float(), nullable=False), sa.Column("evaluated_by", sa.String(128), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False), *_timestamps(),
    )
    op.create_index("ix_knowledge_quality_version", "knowledge_quality_runs", ["tenant_id", "version_id", "created_at"])

    op.create_table(
        "knowledge_reindex_jobs",
        sa.Column("job_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.String(128), sa.ForeignKey("knowledge_document_versions.version_id", ondelete="CASCADE"), nullable=False),
        sa.Column("migration_id", sa.String(128)),
        sa.Column("action", sa.String(24), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("embedding_model", sa.String(160), nullable=False), sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("index_version", sa.String(100), nullable=False), sa.Column("projection_fingerprint", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("stale_chunk_count", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False), sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)), sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("error_code", sa.String(100)),
        sa.Column("error_sha256", sa.String(64)), sa.Column("requested_by", sa.String(128), nullable=False), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_knowledge_reindex_idempotency"),
    )
    op.create_index("ix_knowledge_reindex_status", "knowledge_reindex_jobs", ["tenant_id", "status", "next_attempt_at"])
    op.create_index("ix_knowledge_reindex_migration", "knowledge_reindex_jobs", ["tenant_id", "migration_id"])

    op.create_table(
        "knowledge_index_migrations",
        sa.Column("migration_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_embedding_model", sa.String(160), nullable=False), sa.Column("from_dimensions", sa.Integer(), nullable=False),
        sa.Column("from_index_version", sa.String(100), nullable=False), sa.Column("to_embedding_model", sa.String(160), nullable=False),
        sa.Column("to_dimensions", sa.Integer(), nullable=False), sa.Column("to_index_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("approved_by", sa.String(128)), sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)), *_timestamps(),
    )
    op.create_index("ix_knowledge_index_migration_tenant_status", "knowledge_index_migrations", ["tenant_id", "status"])

    op.create_table(
        "knowledge_retrieval_drift_events",
        sa.Column("drift_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", sa.String(128)), sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False), sa.Column("baseline_metrics", sa.JSON(), nullable=False),
        sa.Column("observed_metrics", sa.JSON(), nullable=False), sa.Column("deltas", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False), sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("evaluated_by", sa.String(128), nullable=False), *_timestamps(),
    )
    op.create_index("ix_knowledge_drift_tenant_created", "knowledge_retrieval_drift_events", ["tenant_id", "created_at"])

    op.create_table(
        "knowledge_releases",
        sa.Column("release_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_key", sa.String(180), nullable=False), sa.Column("release_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False), sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("approved_by", sa.String(128)), sa.Column("approval_reason", sa.String(1000)),
        sa.Column("promoted_at", sa.DateTime(timezone=True)), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "release_key", "release_version", name="uq_knowledge_release_version"),
    )
    op.create_index("ix_knowledge_release_tenant_status", "knowledge_releases", ["tenant_id", "status", "created_at"])

    op.create_table(
        "knowledge_release_items",
        sa.Column("release_item_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", sa.String(128), sa.ForeignKey("knowledge_releases.release_id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.String(128), sa.ForeignKey("knowledge_document_versions.version_id"), nullable=False),
        sa.Column("document_id", sa.String(128), nullable=False), sa.Column("content_sha256", sa.String(64), nullable=False), *_timestamps(),
        sa.UniqueConstraint("tenant_id", "release_id", "version_id", name="uq_knowledge_release_item"),
    )
    op.create_index("ix_knowledge_release_item_release", "knowledge_release_items", ["tenant_id", "release_id"])

    op.create_table(
        "knowledge_governance_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False), sa.Column("actor_user_id", sa.String(128), nullable=False),
        sa.Column("subject_type", sa.String(50), nullable=False), sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False), sa.Column("details_sha256", sa.String(64), nullable=False), *_timestamps(),
    )
    op.create_index("ix_knowledge_event_tenant_created", "knowledge_governance_events", ["tenant_id", "created_at"])


    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_guard_knowledge_version_content() RETURNS trigger AS $$
    BEGIN
      IF NEW.document_id IS DISTINCT FROM OLD.document_id
         OR NEW.version IS DISTINCT FROM OLD.version
         OR NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256
         OR NEW.content_locator IS DISTINCT FROM OLD.content_locator
         OR NEW.rag_source_id IS DISTINCT FROM OLD.rag_source_id
         OR NEW.rag_source_version IS DISTINCT FROM OLD.rag_source_version
         OR NEW.valid_from IS DISTINCT FROM OLD.valid_from
         OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
         OR NEW.metadata IS DISTINCT FROM OLD.metadata
         OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION 'knowledge version content/identity is immutable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute('CREATE TRIGGER knowledge_document_versions_content_immutable BEFORE UPDATE ON "knowledge_document_versions" FOR EACH ROW EXECUTE FUNCTION medclaimiq_guard_knowledge_version_content()')
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_guard_knowledge_release_manifest() RETURNS trigger AS $$
    BEGIN
      IF NEW.release_key IS DISTINCT FROM OLD.release_key
         OR NEW.release_version IS DISTINCT FROM OLD.release_version
         OR NEW.manifest IS DISTINCT FROM OLD.manifest
         OR NEW.manifest_sha256 IS DISTINCT FROM OLD.manifest_sha256
         OR NEW.requested_by IS DISTINCT FROM OLD.requested_by THEN
        RAISE EXCEPTION 'knowledge release manifest is immutable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute('CREATE TRIGGER knowledge_releases_manifest_immutable BEFORE UPDATE ON "knowledge_releases" FOR EACH ROW EXECUTE FUNCTION medclaimiq_guard_knowledge_release_manifest()')

    for table in TABLES:
        _rls(table)
    for table in IMMUTABLE:
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_guard_knowledge_release_manifest()")
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_guard_knowledge_version_content()")
