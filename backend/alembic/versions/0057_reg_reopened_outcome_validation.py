"""reopened-issue outcome validation and recurrence closure assurance
Revision ID: 0057_reg_reopened_outcome_validation
Revises: 0056_reg_post_closure_surveillance
"""
from alembic import op
import sqlalchemy as sa
revision = "0057_reg_reopened_outcome_validation"
down_revision = "0056_reg_post_closure_surveillance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("reopened_remediation_outcomes",
      sa.Column("outcome_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("deficiency_key", sa.String(160), nullable=False, index=True), sa.Column("reopen_investigation_id", sa.String(128), nullable=False, index=True),
      sa.Column("renewed_remediation_refs", sa.JSON(), nullable=False), sa.Column("corrective_action_refs", sa.JSON(), nullable=False), sa.Column("milestone_refs", sa.JSON(), nullable=False),
      sa.Column("prior_root_cause_refs", sa.JSON(), nullable=False), sa.Column("current_root_cause_refs", sa.JSON(), nullable=False), sa.Column("cross_entity_scope", sa.JSON(), nullable=False),
      sa.Column("renewed_commitment_refs", sa.JSON(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("reopened_control_revalidations",
      sa.Column("revalidation_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("deficiency_key", sa.String(160), nullable=False, index=True), sa.Column("outcome_id", sa.String(128), nullable=False, index=True), sa.Column("control_ref", sa.JSON(), nullable=False),
      sa.Column("prior_effectiveness_score", sa.Float(), nullable=False), sa.Column("current_effectiveness_score", sa.Float(), nullable=False), sa.Column("recurrence_containment_score", sa.Float(), nullable=False),
      sa.Column("retest_evidence_refs", sa.JSON(), nullable=False), sa.Column("independent_evidence_refs", sa.JSON(), nullable=False), sa.Column("cross_entity_validation_refs", sa.JSON(), nullable=False),
      sa.Column("independently_validated", sa.Boolean(), nullable=False), sa.Column("validated_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True),
      sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table("recurrence_closure_assurance",
      sa.Column("assurance_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("deficiency_key", sa.String(160), nullable=False, index=True), sa.Column("version", sa.Integer(), nullable=False), sa.Column("outcome_id", sa.String(128), nullable=False, index=True),
      sa.Column("revalidation_refs", sa.JSON(), nullable=False), sa.Column("sustainability_window_days", sa.Integer(), nullable=False), sa.Column("sustainability_evidence_refs", sa.JSON(), nullable=False),
      sa.Column("second_recurrence_count", sa.Integer(), nullable=False), sa.Column("second_recurrence_escalated", sa.Boolean(), nullable=False), sa.Column("readiness_score", sa.Float(), nullable=False),
      sa.Column("blockers", sa.JSON(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
      sa.UniqueConstraint("tenant_id", "deficiency_key", "version", name="uq_recurrence_closure_version"))
    op.create_table("reopened_issue_recertifications",
      sa.Column("recertification_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("deficiency_key", sa.String(160), nullable=False, index=True), sa.Column("assurance_id", sa.String(128), nullable=False, index=True), sa.Column("decision", sa.String(32), nullable=False),
      sa.Column("rationale", sa.Text(), nullable=False), sa.Column("certification_refs", sa.JSON(), nullable=False), sa.Column("decided_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
      sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("reopened_issue_recertifications")
    op.drop_table("recurrence_closure_assurance")
    op.drop_table("reopened_control_revalidations")
    op.drop_table("reopened_remediation_outcomes")
