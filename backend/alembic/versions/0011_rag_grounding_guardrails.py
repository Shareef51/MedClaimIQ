"""Add immutable RAG grounding guardrail audit records.

Revision ID: 0011_rag_grounding_guardrails
Revises: 0010_cross_source_evidence_fusion
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0011_rag_grounding_guardrails"
down_revision: str | None = "0010_cross_source_evidence_fusion"
branch_labels = None
depends_on = None

TABLES = (
    "rag_guardrail_runs",
    "rag_prompt_injection_findings",
    "rag_statement_grounding_checks",
    "rag_guardrail_repair_attempts",
    "rag_human_review_escalations",
)


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
        "rag_guardrail_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("candidate_sha256", sa.String(64), nullable=True),
        sa.Column("guardrail_version", sa.String(120), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("answerable", sa.Boolean(), nullable=False),
        sa.Column("answerability_score", sa.Float(), nullable=False),
        sa.Column("evidence_quality", sa.Float(), nullable=False),
        sa.Column("safe_evidence_count", sa.Integer(), nullable=False),
        sa.Column("excluded_injection_count", sa.Integer(), nullable=False),
        sa.Column("supported_statement_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unsupported_statement_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unresolved_material_contradictions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repair_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalation_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("query_length >= 0 AND safe_evidence_count >= 0 AND excluded_injection_count >= 0", name="rag_guardrail_nonnegative"),
        sa.CheckConstraint("evidence_quality >= 0 AND evidence_quality <= 1", name="guardrail_quality_range"),
        sa.CheckConstraint("answerability_score >= 0 AND answerability_score <= 1", name="guardrail_answerability_range"),
    )
    for name, cols in (
        ("ix_rag_guardrail_runs_tenant_id", ["tenant_id"]),
        ("ix_rag_guardrail_runs_claim_id", ["claim_id"]),
        ("ix_rag_guardrail_runs_pack_id", ["pack_id"]),
        ("ix_rag_guardrail_claim", ["tenant_id", "claim_id", "created_at"]),
        ("ix_rag_guardrail_pack", ["tenant_id", "pack_id"]),
    ):
        op.create_index(name, "rag_guardrail_runs", cols)

    op.create_table(
        "rag_prompt_injection_findings",
        sa.Column("finding_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_key", sa.String(128), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("risk", sa.String(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rule_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="rag_injection_score_range"),
    )
    for name, cols in (
        ("ix_rag_prompt_injection_findings_tenant_id", ["tenant_id"]),
        ("ix_rag_prompt_injection_findings_claim_id", ["claim_id"]),
        ("ix_rag_prompt_injection_findings_run_id", ["run_id"]),
        ("ix_rag_injection_run", ["tenant_id", "run_id", "risk"]),
    ):
        op.create_index(name, "rag_prompt_injection_findings", cols)

    op.create_table(
        "rag_statement_grounding_checks",
        sa.Column("check_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("statement_id", sa.String(128), nullable=False),
        sa.Column("statement_sha256", sa.String(64), nullable=False),
        sa.Column("support_status", sa.String(30), nullable=False),
        sa.Column("support_score", sa.Float(), nullable=False),
        sa.Column("citation_status", sa.String(30), nullable=False),
        sa.Column("cited_evidence_keys", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("invalid_evidence_keys", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("numeric_integrity", sa.Boolean(), nullable=False),
        sa.Column("medical_code_integrity", sa.Boolean(), nullable=False),
        sa.Column("contradiction_safe", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("support_score >= 0 AND support_score <= 1", name="rag_statement_score_range"),
    )
    for name, cols in (
        ("ix_rag_statement_grounding_checks_tenant_id", ["tenant_id"]),
        ("ix_rag_statement_grounding_checks_claim_id", ["claim_id"]),
        ("ix_rag_statement_grounding_checks_run_id", ["run_id"]),
        ("ix_rag_statement_run", ["tenant_id", "run_id", "support_status"]),
    ):
        op.create_index(name, "rag_statement_grounding_checks", cols)

    op.create_table(
        "rag_guardrail_repair_attempts",
        sa.Column("repair_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(80), nullable=False),
        sa.Column("query_sha256", sa.String(64), nullable=False),
        sa.Column("requested_retrievers", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("result_pack_id", sa.String(128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("answerable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_number >= 1 AND attempt_number <= 5", name="rag_repair_attempt_range"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="rag_repair_confidence_range"),
    )
    for name, cols in (
        ("ix_rag_guardrail_repair_attempts_tenant_id", ["tenant_id"]),
        ("ix_rag_guardrail_repair_attempts_claim_id", ["claim_id"]),
        ("ix_rag_guardrail_repair_attempts_run_id", ["run_id"]),
        ("ix_rag_repair_run", ["tenant_id", "run_id", "attempt_number"]),
    ):
        op.create_index(name, "rag_guardrail_repair_attempts", cols)

    op.create_table(
        "rag_human_review_escalations",
        sa.Column("escalation_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(128), sa.ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_id", sa.String(128), sa.ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_decision", sa.String(30), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("status", sa.String(30), nullable=False, server_default="requested"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols in (
        ("ix_rag_human_review_escalations_tenant_id", ["tenant_id"]),
        ("ix_rag_human_review_escalations_claim_id", ["claim_id"]),
        ("ix_rag_human_review_escalations_run_id", ["run_id"]),
        ("ix_rag_human_review_escalations_pack_id", ["pack_id"]),
        ("ix_rag_human_escalation_claim", ["tenant_id", "claim_id", "created_at"]),
        ("ix_rag_human_escalation_run", ["tenant_id", "run_id"]),
    ):
        op.create_index(name, "rag_human_review_escalations", cols)

    for table in TABLES:
        _tenant_rls(table)

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_guardrail_audit_mutation()
    RETURNS trigger AS $$ BEGIN
      RAISE EXCEPTION 'immutable RAG guardrail audit record';
    END; $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_guardrail_audit_mutation()"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS medclaimiq_reject_guardrail_audit_mutation()")
