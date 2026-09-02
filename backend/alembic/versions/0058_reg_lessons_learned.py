"""regulatory remediation lessons learned, enterprise control improvement and feedback integration

Revision ID: 0058_reg_lessons_learned
Revises: 0057_reg_reopened_outcome_validation
"""
from alembic import op
import sqlalchemy as sa

revision = "0058_reg_lessons_learned"
down_revision = "0057_reg_reopened_outcome_validation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("regulatory_remediation_lessons",
        sa.Column("lesson_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_key", sa.String(180), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("source_outcome_refs", sa.JSON(), nullable=False),
        sa.Column("source_reclosure_refs", sa.JSON(), nullable=False), sa.Column("root_cause_refs", sa.JSON(), nullable=False), sa.Column("control_refs", sa.JSON(), nullable=False),
        sa.Column("successful_pattern_refs", sa.JSON(), nullable=False), sa.Column("failed_pattern_refs", sa.JSON(), nullable=False), sa.Column("affected_entities", sa.JSON(), nullable=False),
        sa.Column("effectiveness_score", sa.Float(), nullable=False), sa.Column("recurrence_risk_score", sa.Float(), nullable=False), sa.Column("lesson_summary", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("tenant_id", "lesson_key", "version", name="uq_reg_lesson_version"))
    op.create_index("ix_reg_lesson_tenant", "regulatory_remediation_lessons", ["tenant_id"])
    op.create_table("regulatory_feedback_observations", sa.Column("feedback_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False), sa.Column("regulator_ref", sa.JSON(), nullable=False), sa.Column("examination_ref", sa.JSON(), nullable=False), sa.Column("correspondence_ref", sa.JSON(), nullable=False), sa.Column("feedback_type", sa.String(80), nullable=False), sa.Column("documented_position", sa.Text(), nullable=False), sa.Column("enterprise_interpretation", sa.Text(), nullable=False), sa.Column("ai_observation", sa.Text()), sa.Column("supervisory_themes", sa.JSON(), nullable=False), sa.Column("evidence_refs", sa.JSON(), nullable=False), sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("control_improvement_proposals", sa.Column("proposal_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False), sa.Column("lesson_id", sa.String(128), nullable=False), sa.Column("proposal_type", sa.String(64), nullable=False), sa.Column("target_refs", sa.JSON(), nullable=False), sa.Column("rationale", sa.Text(), nullable=False), sa.Column("expected_benefit", sa.Text(), nullable=False), sa.Column("risk_if_not_adopted", sa.Text(), nullable=False), sa.Column("evidence_refs", sa.JSON(), nullable=False), sa.Column("cross_entity_scope", sa.JSON(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("human_approval_required", sa.Boolean(), nullable=False), sa.Column("proposed_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False), sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("control_improvement_decisions", sa.Column("decision_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False), sa.Column("proposal_id", sa.String(128), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("rationale", sa.Text(), nullable=False), sa.Column("approval_refs", sa.JSON(), nullable=False), sa.Column("decided_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False), sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("regulatory_knowledge_promotions", sa.Column("promotion_id", sa.String(128), primary_key=True), sa.Column("tenant_id", sa.String(128), sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False), sa.Column("lesson_id", sa.String(128), nullable=False), sa.Column("knowledge_target", sa.String(120), nullable=False), sa.Column("source_hashes", sa.JSON(), nullable=False), sa.Column("approved_refs", sa.JSON(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("promoted_by_user_id", sa.String(128), sa.ForeignKey("user_accounts.user_id", ondelete="RESTRICT")), sa.Column("promoted_at", sa.DateTime(timezone=True)))


def downgrade():
    for t in ["regulatory_knowledge_promotions", "control_improvement_decisions", "control_improvement_proposals", "regulatory_feedback_observations", "regulatory_remediation_lessons"]:
        op.drop_table(t)
