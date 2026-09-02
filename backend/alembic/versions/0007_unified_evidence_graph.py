"""Add unified healthcare evidence graph and cross-source normalization.

Revision ID: 0007_unified_evidence_graph
Revises: 0006_healthcare_fhir
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0007_unified_evidence_graph"
down_revision: str | None = "0006_healthcare_fhir"
branch_labels = None
depends_on = None

TABLES = (
    "canonical_entities",
    "source_entity_mappings",
    "canonical_code_mappings",
    "claim_line_crosswalks",
    "evidence_graph_edges",
    "evidence_contradictions",
    "rag_metadata_records",
)


def _tenant_rls(table: str) -> None:
    op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
    op.execute(
        f"""CREATE POLICY {table}_tenant_isolation ON {table}
        USING (tenant_id = current_setting('app.current_tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"""
    )


def upgrade() -> None:
    op.create_table(
        "canonical_entities",
        sa.Column("entity_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("canonical_key", sa.String(512), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True),
        sa.Column("patient_subject_id", sa.String(128), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "entity_type", "canonical_key", name="uq_canonical_entity_key"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_canonical_entity_valid_window"),
    )
    for name, cols in (
        ("ix_canonical_entities_tenant_id", ["tenant_id"]),
        ("ix_canonical_entities_claim_id", ["claim_id"]),
        ("ix_canonical_entities_patient_subject_id", ["patient_subject_id"]),
        ("ix_canonical_entity_tenant_claim", ["tenant_id", "claim_id", "entity_type"]),
        ("ix_canonical_entity_tenant_patient", ["tenant_id", "patient_subject_id", "entity_type"]),
    ):
        op.create_index(name, "canonical_entities", cols)

    op.create_table(
        "source_entity_mappings",
        sa.Column("mapping_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.String(128), sa.ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_type", sa.String(60), nullable=False),
        sa.Column("source_system", sa.String(160), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("content_sha256", sa.String(64), nullable=True),
        sa.Column("source_locator", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.UniqueConstraint("tenant_id", "source_type", "source_system", "resource_type", "resource_id", "source_version", name="uq_source_entity_version"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_source_mapping_confidence"),
        sa.CheckConstraint("authority_rank >= 0 AND authority_rank <= 100", name="ck_source_mapping_authority"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_source_mapping_valid_window"),
    )
    for name, cols in (
        ("ix_source_entity_mappings_tenant_id", ["tenant_id"]),
        ("ix_source_entity_mappings_entity_id", ["entity_id"]),
        ("ix_source_entity_mappings_claim_id", ["claim_id"]),
        ("ix_source_mapping_entity", ["tenant_id", "entity_id"]),
        ("ix_source_mapping_claim", ["tenant_id", "claim_id"]),
    ):
        op.create_index(name, "source_entity_mappings", cols)

    op.create_table(
        "canonical_code_mappings",
        sa.Column("code_mapping_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_system", sa.String(200), nullable=False),
        sa.Column("source_code", sa.String(100), nullable=False),
        sa.Column("canonical_system", sa.String(80), nullable=False),
        sa.Column("canonical_code", sa.String(100), nullable=False),
        sa.Column("display", sa.String(500), nullable=True),
        sa.Column("mapping_method", sa.String(40), nullable=False, server_default="deterministic_alias"),
        sa.Column("mapping_version", sa.String(80), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_system", "source_code", name="uq_code_source"),
    )
    op.create_index("ix_canonical_code_mappings_tenant_id", "canonical_code_mappings", ["tenant_id"])
    op.create_index("ix_code_mapping_canonical", "canonical_code_mappings", ["tenant_id", "canonical_system", "canonical_code"])

    op.create_table(
        "claim_line_crosswalks",
        sa.Column("crosswalk_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_line_id", sa.String(128), sa.ForeignKey("claim_lines.claim_line_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_mapping_id", sa.String(128), sa.ForeignKey("source_entity_mappings.mapping_id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(6, 5), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("service_date_alignment", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "claim_line_id", "source_mapping_id", name="uq_claim_line_crosswalk_candidate"),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_claim_line_crosswalk_score"),
    )
    for name, cols in (
        ("ix_claim_line_crosswalks_tenant_id", ["tenant_id"]),
        ("ix_claim_line_crosswalks_claim_id", ["claim_id"]),
        ("ix_claim_line_crosswalks_claim_line_id", ["claim_line_id"]),
        ("ix_claim_line_crosswalks_source_mapping_id", ["source_mapping_id"]),
        ("ix_crosswalk_claim", ["tenant_id", "claim_id", "status"]),
    ):
        op.create_index(name, "claim_line_crosswalks", cols)

    op.create_table(
        "evidence_graph_edges",
        sa.Column("edge_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_entity_id", sa.String(128), sa.ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", sa.String(128), sa.ForeignKey("canonical_entities.entity_id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(60), nullable=False),
        sa.Column("edge_fingerprint", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("provenance_refs", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "edge_fingerprint", name="uq_evidence_graph_edge"),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_graph_edge_not_self"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_graph_edge_confidence"),
        sa.CheckConstraint("authority_rank >= 0 AND authority_rank <= 100", name="ck_graph_edge_authority"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_graph_edge_valid_window"),
    )
    for name, cols in (
        ("ix_evidence_graph_edges_tenant_id", ["tenant_id"]),
        ("ix_evidence_graph_edges_claim_id", ["claim_id"]),
        ("ix_evidence_graph_edges_source_entity_id", ["source_entity_id"]),
        ("ix_evidence_graph_edges_target_entity_id", ["target_entity_id"]),
        ("ix_graph_edge_source", ["tenant_id", "source_entity_id", "relationship_type"]),
        ("ix_graph_edge_target", ["tenant_id", "target_entity_id", "relationship_type"]),
        ("ix_graph_edge_claim", ["tenant_id", "claim_id"]),
    ):
        op.create_index(name, "evidence_graph_edges", cols)

    op.create_table(
        "evidence_contradictions",
        sa.Column("contradiction_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_entity_id", sa.String(128), sa.ForeignKey("canonical_entities.entity_id", ondelete="SET NULL"), nullable=True),
        sa.Column("field_name", sa.String(120), nullable=False),
        sa.Column("left_mapping_id", sa.String(128), sa.ForeignKey("source_entity_mappings.mapping_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("right_mapping_id", sa.String(128), sa.ForeignKey("source_entity_mappings.mapping_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("left_value", sa.JSON(), nullable=False),
        sa.Column("right_value", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("contradiction_fingerprint", sa.String(64), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "contradiction_fingerprint", name="uq_evidence_contradiction"),
        sa.CheckConstraint("left_mapping_id <> right_mapping_id", name="ck_contradiction_distinct_sources"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_contradiction_confidence"),
    )
    for name, cols in (
        ("ix_evidence_contradictions_tenant_id", ["tenant_id"]),
        ("ix_evidence_contradictions_claim_id", ["claim_id"]),
        ("ix_evidence_contradictions_subject_entity_id", ["subject_entity_id"]),
        ("ix_contradiction_claim", ["tenant_id", "claim_id", "status", "severity"]),
    ):
        op.create_index(name, "evidence_contradictions", cols)

    op.create_table(
        "rag_metadata_records",
        sa.Column("metadata_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(60), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("entity_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("relationship_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("evidence_confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_type", "source_id", "source_version", name="uq_rag_metadata_source_version"),
        sa.CheckConstraint("evidence_confidence >= 0 AND evidence_confidence <= 1", name="ck_rag_metadata_confidence"),
        sa.CheckConstraint("authority_rank >= 0 AND authority_rank <= 100", name="ck_rag_metadata_authority"),
    )
    for name, cols in (
        ("ix_rag_metadata_records_tenant_id", ["tenant_id"]),
        ("ix_rag_metadata_records_claim_id", ["claim_id"]),
        ("ix_rag_metadata_records_patient_subject_id", ["patient_subject_id"]),
        ("ix_rag_metadata_claim", ["tenant_id", "claim_id"]),
        ("ix_rag_metadata_patient", ["tenant_id", "patient_subject_id"]),
    ):
        op.create_index(name, "rag_metadata_records", cols)

    for table in TABLES:
        _tenant_rls(table)

    # Provenance/history projections are append-only. Contradictions remain mutable only for explicit human resolution.
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_graph_history_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'append-only evidence graph history';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in ("source_entity_mappings", "claim_line_crosswalks", "evidence_graph_edges", "rag_metadata_records"):
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_graph_history_mutation()")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_graph_history_mutation()")
