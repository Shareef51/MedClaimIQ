"""regulatory examination systemic recurrence portfolio governance
Revision ID: 0068_reg_exam_systemic_recurrence_portfolio
Revises: 0067_reg_exam_reclosure_sustainability
"""
from alembic import op
import sqlalchemy as sa
revision="0068_reg_exam_systemic_recurrence_portfolio"; down_revision="0067_reg_exam_reclosure_sustainability"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("regulatory_exam_systemic_recurrence_portfolio_snapshots",sa.Column("portfolio_snapshot_id",sa.String(36),primary_key=True),sa.Column("portfolio_id",sa.String(64),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("assessment_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_enterprise_intervention_cases",sa.Column("intervention_case_id",sa.String(36),primary_key=True),sa.Column("portfolio_id",sa.String(64),nullable=False,index=True),sa.Column("systemic_pattern_id",sa.String(64),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_enterprise_intervention_program_versions",sa.Column("intervention_program_version_id",sa.String(36),primary_key=True),sa.Column("intervention_case_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_enterprise_intervention_challenges",sa.Column("challenge_version_id",sa.String(36),primary_key=True),sa.Column("intervention_case_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("conclusion",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_enterprise_intervention_challenges"); op.drop_table("regulatory_exam_enterprise_intervention_program_versions"); op.drop_table("regulatory_exam_enterprise_intervention_cases"); op.drop_table("regulatory_exam_systemic_recurrence_portfolio_snapshots")
