"""Add FHIR connection, resource snapshots, provenance, identity matching, verification, and healthcare events.

Revision ID: 0006_healthcare_fhir
Revises: 0005_document_intelligence
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision: str = "0006_healthcare_fhir"
down_revision: str | None = "0005_document_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fhir_connections",
        sa.Column("connection_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_key", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(180), nullable=False),
        sa.Column("base_url", sa.String(1024), nullable=False),
        sa.Column("fhir_version", sa.String(32), nullable=False, server_default="4.0.1"),
        sa.Column("auth_mode", sa.String(60), nullable=False, server_default="smart_backend_services"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("rate_limit_per_second", sa.Numeric(8,2), nullable=False, server_default="10"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("config_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id","connection_key",name="uq_fhir_connections_connection_key_per_tenant"),
    )
    op.create_index("ix_fhir_connections_tenant_id","fhir_connections",["tenant_id"])
    op.create_index("ix_fhir_connection_tenant_status","fhir_connections",["tenant_id","status"])

    op.create_table(
        "fhir_resource_snapshots",
        sa.Column("snapshot_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("connection_id",sa.String(128),sa.ForeignKey("fhir_connections.connection_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="SET NULL"),nullable=True),
        sa.Column("patient_subject_id",sa.String(128),nullable=True),
        sa.Column("resource_type",sa.String(80),nullable=False),
        sa.Column("logical_id",sa.String(256),nullable=False),
        sa.Column("version_id",sa.String(128),nullable=False),
        sa.Column("last_updated",sa.DateTime(timezone=True),nullable=True),
        sa.Column("source_url",sa.String(1500),nullable=False),
        sa.Column("content_sha256",sa.String(64),nullable=False),
        sa.Column("raw_resource",sa.JSON(),nullable=False),
        sa.Column("canonical_resource",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("authoritative",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("fetched_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","connection_id","resource_type","logical_id","version_id",name="uq_fhir_resource_snapshots_fhir_version_per_connection"),
    )
    for name, cols in (
        ("ix_fhir_resource_snapshots_tenant_id",["tenant_id"]),("ix_fhir_resource_snapshots_connection_id",["connection_id"]),
        ("ix_fhir_resource_snapshots_claim_id",["claim_id"]),("ix_fhir_resource_snapshots_patient_subject_id",["patient_subject_id"]),
        ("ix_fhir_snapshot_tenant_resource",["tenant_id","resource_type","logical_id"]),("ix_fhir_snapshot_tenant_claim",["tenant_id","claim_id"]),
        ("ix_fhir_snapshot_tenant_patient",["tenant_id","patient_subject_id"]),
    ): op.create_index(name,"fhir_resource_snapshots",cols)

    op.create_table(
        "fhir_provenance",
        sa.Column("provenance_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("snapshot_id",sa.String(128),sa.ForeignKey("fhir_resource_snapshots.snapshot_id",ondelete="CASCADE"),nullable=False),
        sa.Column("source_system",sa.String(160),nullable=False),
        sa.Column("source_endpoint",sa.String(1500),nullable=False),
        sa.Column("fetched_by",sa.String(120),nullable=False,server_default="fhir_gateway"),
        sa.Column("trace_id",sa.String(128),nullable=True),
        sa.Column("request_metadata",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("recorded_at",sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index("ix_fhir_provenance_tenant_id","fhir_provenance",["tenant_id"])
    op.create_index("ix_fhir_provenance_snapshot_id","fhir_provenance",["snapshot_id"])
    op.create_index("ix_fhir_provenance_tenant_snapshot","fhir_provenance",["tenant_id","snapshot_id"])

    op.create_table(
        "patient_identity_matches",
        sa.Column("match_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("patient_subject_id",sa.String(128),nullable=False),
        sa.Column("connection_id",sa.String(128),sa.ForeignKey("fhir_connections.connection_id",ondelete="CASCADE"),nullable=False),
        sa.Column("fhir_patient_id",sa.String(256),nullable=False),
        sa.Column("score",sa.Numeric(6,5),nullable=False),
        sa.Column("status",sa.String(40),nullable=False),
        sa.Column("reasons",sa.JSON(),nullable=False,server_default=sa.text("'[]'::json")),
        sa.Column("resolved_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="SET NULL"),nullable=True),
        sa.Column("resolved_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","patient_subject_id","connection_id","fhir_patient_id",name="uq_patient_identity_matches_identity_candidate_per_source"),
        sa.CheckConstraint("score >= 0 AND score <= 1",name="ck_patient_identity_matches_score_range"),
    )
    for name,cols in (("ix_patient_identity_matches_tenant_id",["tenant_id"]),("ix_patient_identity_matches_connection_id",["connection_id"]),("ix_identity_match_tenant_patient",["tenant_id","patient_subject_id","status"])): op.create_index(name,"patient_identity_matches",cols)

    op.create_table(
        "hospital_cross_verifications",
        sa.Column("verification_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("snapshot_id",sa.String(128),sa.ForeignKey("fhir_resource_snapshots.snapshot_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("verification_type",sa.String(80),nullable=False),
        sa.Column("status",sa.String(40),nullable=False),
        sa.Column("confidence",sa.Numeric(6,5),nullable=False),
        sa.Column("findings",sa.JSON(),nullable=False,server_default=sa.text("'[]'::json")),
        sa.Column("input_snapshot",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("trace_id",sa.String(128),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","claim_id","snapshot_id","verification_type",name="uq_hospital_cross_verifications_verification_per_snapshot"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1",name="ck_hospital_cross_verifications_confidence_range"),
    )
    for name,cols in (("ix_hospital_cross_verifications_tenant_id",["tenant_id"]),("ix_hospital_cross_verifications_claim_id",["claim_id"]),("ix_hospital_cross_verifications_snapshot_id",["snapshot_id"]),("ix_hospital_verification_tenant_claim",["tenant_id","claim_id","status"])): op.create_index(name,"hospital_cross_verifications",cols)

    op.create_table(
        "healthcare_events",
        sa.Column("event_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=True),
        sa.Column("event_type",sa.String(120),nullable=False),
        sa.Column("aggregate_type",sa.String(80),nullable=False),
        sa.Column("aggregate_id",sa.String(160),nullable=False),
        sa.Column("payload",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")),
        sa.Column("idempotency_key",sa.String(180),nullable=False),
        sa.Column("trace_id",sa.String(128),nullable=True),
        sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_healthcare_events_healthcare_event_idempotency_per_tenant"),
    )
    op.create_index("ix_healthcare_events_tenant_id","healthcare_events",["tenant_id"])
    op.create_index("ix_healthcare_events_claim_id","healthcare_events",["claim_id"])
    op.create_index("ix_healthcare_event_tenant_claim","healthcare_events",["tenant_id","claim_id","occurred_at"])

    op.create_table(
        "healthcare_event_outbox",
        sa.Column("outbox_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("event_id",sa.String(128),sa.ForeignKey("healthcare_events.event_id",ondelete="CASCADE"),nullable=False),
        sa.Column("topic",sa.String(180),nullable=False,server_default="medclaimiq.healthcare.events.v1"),
        sa.Column("partition_key",sa.String(160),nullable=False),
        sa.Column("payload",sa.JSON(),nullable=False),
        sa.Column("published_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("publish_attempts",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("last_error",sa.Text(),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("event_id",name="uq_healthcare_event_outbox_healthcare_outbox_event_once"),
    )
    op.create_index("ix_healthcare_event_outbox_tenant_id","healthcare_event_outbox",["tenant_id"])
    op.create_index("ix_healthcare_outbox_unpublished","healthcare_event_outbox",["published_at","created_at"])

    for table in ("fhir_connections","fhir_resource_snapshots","fhir_provenance","patient_identity_matches","hospital_cross_verifications","healthcare_events","healthcare_event_outbox"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_fhir_append_only_mutation() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'append-only FHIR evidence record cannot be updated or deleted'; END; $$ LANGUAGE plpgsql;
    """)
    for table in ("fhir_resource_snapshots","fhir_provenance","hospital_cross_verifications","healthcare_events"):
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_fhir_append_only_mutation()")


def downgrade() -> None:
    for table in ("fhir_resource_snapshots","fhir_provenance","hospital_cross_verifications","healthcare_events"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.drop_table("healthcare_event_outbox")
    op.drop_table("healthcare_events")
    op.drop_table("hospital_cross_verifications")
    op.drop_table("patient_identity_matches")
    op.drop_table("fhir_provenance")
    op.drop_table("fhir_resource_snapshots")
    op.drop_table("fhir_connections")
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_fhir_append_only_mutation()")
