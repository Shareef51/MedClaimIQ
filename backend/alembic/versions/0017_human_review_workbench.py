"""Human review queue, workbench and decision operations.

Revision ID: 0017_human_review_workbench
Revises: 0016_sla_deadline_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_human_review_workbench"
down_revision = "0016_sla_deadline_engine"
branch_labels = None
depends_on = None

TABLES = (
    "review_work_items", "review_claim_locks", "reviewer_notes",
    "review_action_events", "review_decision_metadata",
)
IMMUTABLE = ("reviewer_notes", "review_action_events", "review_decision_metadata")


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
        "review_work_items",
        sa.Column("work_item_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("priority_band", sa.String(20), nullable=False),
        sa.Column("priority_reasons", sa.JSON(), nullable=False),
        sa.Column("assigned_reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="SET NULL")),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "claim_id", name="uq_review_work_item_claim"),
    )
    op.create_index("ix_review_work_queue", "review_work_items", ["tenant_id", "status", "priority_score", "created_at"])
    op.create_index("ix_review_work_assignee", "review_work_items", ["tenant_id", "assigned_reviewer_user_id", "status"])

    op.create_table(
        "review_claim_locks",
        sa.Column("lock_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("lock_token_sha256", sa.String(64), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "claim_id", name="uq_review_claim_lock"),
    )
    op.create_index("ix_review_lock_expiry", "review_claim_locks", ["tenant_id", "locked_until"])

    op.create_table(
        "reviewer_notes",
        sa.Column("note_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("note_type", sa.String(30), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_sha256", sa.String(64), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reviewer_note_claim", "reviewer_notes", ["tenant_id", "claim_id", "created_at"])

    op.create_table(
        "review_action_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("reviewer_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_review_action_idempotency"),
    )
    op.create_index("ix_review_action_claim", "review_action_events", ["tenant_id", "claim_id", "sequence"])

    op.create_table(
        "review_decision_metadata",
        sa.Column("metadata_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.String(128), sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_id", sa.String(128), sa.ForeignKey("human_review_decisions.decision_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("ai_recommendation", sa.String(80)),
        sa.Column("override_ai_recommendation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("override_reason", sa.Text()),
        sa.Column("expected_claim_status_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_decision_meta_claim", "review_decision_metadata", ["tenant_id", "claim_id", "created_at"])

    for table in TABLES:
        _rls(table)
    for table in IMMUTABLE:
        op.execute(
            f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" '
            'FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()'
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
