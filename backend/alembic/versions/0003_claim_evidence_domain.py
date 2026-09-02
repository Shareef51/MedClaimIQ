"""Persist tenant-isolated claim and evidence domain with immutable provenance events.

Revision ID: 0003_claim_evidence_domain
Revises: 0002_oidc_authentication_sessions
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0003_claim_evidence_domain"
down_revision: str | None = "0002_oidc_authentication_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("patient_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("external_identifiers", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("synthetic_data", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "patient_subject_id", name="uq_patients_subject_per_tenant"),
    )
    op.create_index("ix_patients_tenant_id", "patients", ["tenant_id"])
    op.create_index("ix_patients_patient_subject_id", "patients", ["patient_subject_id"])
    op.create_index("ix_patient_tenant_status", "patients", ["tenant_id", "status"])

    op.create_table(
        "providers",
        sa.Column("provider_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_ref", sa.String(160), nullable=False),
        sa.Column("provider_type", sa.String(60), nullable=False),
        sa.Column("external_identifiers", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider_ref", name="uq_providers_provider_ref_per_tenant"),
    )
    op.create_index("ix_providers_tenant_id", "providers", ["tenant_id"])
    op.create_index("ix_providers_organization_id", "providers", ["organization_id"])
    op.create_index("ix_provider_tenant_org", "providers", ["tenant_id", "organization_id"])

    op.create_table(
        "policies",
        sa.Column("policy_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("payer_organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("policy_ref", sa.String(160), nullable=False),
        sa.Column("plan_name", sa.String(180), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_policies_valid_window"),
    )
    op.create_index("ix_policies_tenant_id", "policies", ["tenant_id"])
    op.create_index("ix_policies_patient_subject_id", "policies", ["patient_subject_id"])
    op.create_index("ix_policies_payer_organization_id", "policies", ["payer_organization_id"])
    op.create_index("ix_policy_tenant_subject", "policies", ["tenant_id", "patient_subject_id"])
    op.create_index("ix_policy_effective_window", "policies", ["tenant_id", "effective_from", "effective_to"])

    op.create_table(
        "encounters",
        sa.Column("encounter_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("provider_organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_ref", sa.String(160), nullable=False),
        sa.Column("encounter_type", sa.String(80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_system", sa.String(120), nullable=False),
        sa.Column("external_identifiers", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_encounters_valid_window"),
    )
    op.create_index("ix_encounters_tenant_id", "encounters", ["tenant_id"])
    op.create_index("ix_encounters_patient_subject_id", "encounters", ["patient_subject_id"])
    op.create_index("ix_encounters_provider_organization_id", "encounters", ["provider_organization_id"])
    op.create_index("ix_encounter_tenant_subject", "encounters", ["tenant_id", "patient_subject_id"])
    op.create_index("ix_encounter_tenant_provider", "encounters", ["tenant_id", "provider_organization_id"])

    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_claim_ref", sa.String(160), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("provider_organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_organization_id", sa.String(128), sa.ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("policy_id", sa.String(128), sa.ForeignKey("policies.policy_id", ondelete="SET NULL"), nullable=True),
        sa.Column("encounter_id", sa.String(128), sa.ForeignKey("encounters.encounter_id", ondelete="SET NULL"), nullable=True),
        sa.Column("claim_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("status_version", sa.Integer(), nullable=False),
        sa.Column("assigned_reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("service_from", sa.Date(), nullable=False),
        sa.Column("service_to", sa.Date(), nullable=True),
        sa.Column("ai_review_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("human_review_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_amount >= 0", name="ck_claims_nonnegative_total"),
        sa.CheckConstraint("service_to IS NULL OR service_to >= service_from", name="ck_claims_valid_service_window"),
        sa.UniqueConstraint("tenant_id", "external_claim_ref", name="uq_claims_external_ref_per_tenant"),
    )
    op.create_index("ix_claims_tenant_id", "claims", ["tenant_id"])
    op.create_index("ix_claims_patient_subject_id", "claims", ["patient_subject_id"])
    op.create_index("ix_claims_provider_organization_id", "claims", ["provider_organization_id"])
    op.create_index("ix_claims_payer_organization_id", "claims", ["payer_organization_id"])
    op.create_index("ix_claims_policy_id", "claims", ["policy_id"])
    op.create_index("ix_claims_encounter_id", "claims", ["encounter_id"])
    op.create_index("ix_claims_status", "claims", ["status"])
    op.create_index("ix_claims_assigned_reviewer_user_id", "claims", ["assigned_reviewer_user_id"])
    op.create_index("ix_claim_tenant_patient", "claims", ["tenant_id", "patient_subject_id"])
    op.create_index("ix_claim_tenant_status", "claims", ["tenant_id", "status"])
    op.create_index("ix_claim_tenant_reviewer", "claims", ["tenant_id", "assigned_reviewer_user_id"])

    op.create_table(
        "claim_lines",
        sa.Column("claim_line_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("code_system", sa.String(40), nullable=False),
        sa.Column("service_code", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("units", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("provider_id", sa.String(128), sa.ForeignKey("providers.provider_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("line_number > 0", name="ck_claim_lines_positive_line_number"),
        sa.CheckConstraint("units > 0", name="ck_claim_lines_positive_units"),
        sa.CheckConstraint("amount >= 0", name="ck_claim_lines_nonnegative_amount"),
        sa.UniqueConstraint("tenant_id", "claim_id", "line_number", name="uq_claim_lines_line_number_per_claim"),
    )
    op.create_index("ix_claim_lines_tenant_id", "claim_lines", ["tenant_id"])
    op.create_index("ix_claim_lines_claim_id", "claim_lines", ["claim_id"])
    op.create_index("ix_claim_lines_provider_id", "claim_lines", ["provider_id"])
    op.create_index("ix_claim_line_tenant_claim", "claim_lines", ["tenant_id", "claim_id"])
    op.create_index("ix_claim_line_code", "claim_lines", ["tenant_id", "code_system", "service_code"])

    op.create_table(
        "evidence_artifacts",
        sa.Column("evidence_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_subject_id", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_system", sa.String(120), nullable=False),
        sa.Column("source_locator", sa.JSON(), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("media_type", sa.String(160), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("evidence_version", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authoritative", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "claim_id", "content_sha256", name="uq_evidence_artifacts_content_per_claim"),
    )
    op.create_index("ix_evidence_artifacts_tenant_id", "evidence_artifacts", ["tenant_id"])
    op.create_index("ix_evidence_artifacts_claim_id", "evidence_artifacts", ["claim_id"])
    op.create_index("ix_evidence_artifacts_patient_subject_id", "evidence_artifacts", ["patient_subject_id"])
    op.create_index("ix_evidence_tenant_claim", "evidence_artifacts", ["tenant_id", "claim_id"])
    op.create_index("ix_evidence_tenant_status", "evidence_artifacts", ["tenant_id", "status"])
    op.create_index("ix_evidence_tenant_document_type", "evidence_artifacts", ["tenant_id", "document_type"])

    op.create_table(
        "evidence_lineage",
        sa.Column("lineage_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_evidence_id", sa.String(128), sa.ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_evidence_id", sa.String(128), sa.ForeignKey("evidence_artifacts.evidence_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relationship", sa.String(40), nullable=False),
        sa.Column("transformation_name", sa.String(120), nullable=True),
        sa.Column("transformation_version", sa.String(80), nullable=True),
        sa.Column("transformation_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "child_evidence_id", "parent_evidence_id", "relationship", name="uq_evidence_lineage_unique_edge"),
    )
    op.create_index("ix_evidence_lineage_tenant_id", "evidence_lineage", ["tenant_id"])
    op.create_index("ix_evidence_lineage_claim_id", "evidence_lineage", ["claim_id"])
    op.create_index("ix_lineage_tenant_child", "evidence_lineage", ["tenant_id", "child_evidence_id"])
    op.create_index("ix_lineage_tenant_parent", "evidence_lineage", ["tenant_id", "parent_evidence_id"])

    op.create_table(
        "claim_status_events",
        sa.Column("status_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=False),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_claim_status_events_idempotency_per_tenant"),
        sa.UniqueConstraint("tenant_id", "claim_id", "to_version", name="uq_claim_status_events_version_per_claim"),
    )
    op.create_index("ix_claim_status_events_tenant_id", "claim_status_events", ["tenant_id"])
    op.create_index("ix_claim_status_events_claim_id", "claim_status_events", ["claim_id"])
    op.create_index("ix_claim_status_event_claim", "claim_status_events", ["tenant_id", "claim_id", "to_version"])

    op.create_table(
        "human_review_decisions",
        sa.Column("decision_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_human_review_decisions_decision_idempotency_per_tenant"),
    )
    op.create_index("ix_human_review_decisions_tenant_id", "human_review_decisions", ["tenant_id"])
    op.create_index("ix_human_review_decisions_claim_id", "human_review_decisions", ["claim_id"])
    op.create_index("ix_human_review_decisions_reviewer_user_id", "human_review_decisions", ["reviewer_user_id"])
    op.create_index("ix_human_decision_claim", "human_review_decisions", ["tenant_id", "claim_id", "decided_at"])

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_audit_events_audit_idempotency_per_tenant"),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_tenant_resource", "audit_events", ["tenant_id", "resource_type", "resource_id"])
    op.create_index("ix_audit_tenant_occurred", "audit_events", ["tenant_id", "occurred_at"])

    # Defense-in-depth isolation. Repositories retain explicit tenant predicates.
    tenant_tables = (
        "patients",
        "providers",
        "policies",
        "encounters",
        "claims",
        "claim_lines",
        "evidence_artifacts",
        "evidence_lineage",
        "claim_status_events",
        "human_review_decisions",
        "audit_events",
    )
    for table in tenant_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
        )

    # Append-only records provide traceable provenance. Application code has no update/delete
    # repository methods; PostgreSQL independently rejects mutation attempts.
    op.execute(
        "CREATE OR REPLACE FUNCTION medclaimiq_reject_immutable_mutation() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'immutable MedClaimIQ record cannot be modified'; END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER evidence_lineage_immutable BEFORE UPDATE OR DELETE ON evidence_lineage "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )
    op.execute(
        "CREATE TRIGGER claim_status_events_immutable BEFORE UPDATE OR DELETE ON claim_status_events "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )
    op.execute(
        "CREATE TRIGGER human_review_decisions_immutable BEFORE UPDATE OR DELETE ON human_review_decisions "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )
    op.execute(
        "CREATE TRIGGER audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_mutation()"
    )


def downgrade() -> None:
    for table in ("evidence_lineage", "claim_status_events", "human_review_decisions", "audit_events"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_immutable_mutation()")
    for table in (
        "audit_events",
        "human_review_decisions",
        "claim_status_events",
        "evidence_lineage",
        "evidence_artifacts",
        "claim_lines",
        "claims",
        "encounters",
        "policies",
        "providers",
        "patients",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.drop_table(table)
