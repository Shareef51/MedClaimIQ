"""regulatory examination reopened enterprise intervention
Revision ID: 0072_reg_exam_reopened_enterprise_intervention
Revises: 0071_reg_exam_post_intervention_surveillance
"""
from alembic import op
import sqlalchemy as sa
revision="0072_reg_exam_reopened_enterprise_intervention"; down_revision="0071_reg_exam_post_intervention_surveillance"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("reg_exam_reopened_enterprise_intervention_plans",sa.Column("reopened_intervention_plan_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reopening_version_id",sa.String(36),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reopened_enterprise_independent_revalidations",sa.Column("independent_revalidation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("result",sa.String(32),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reopened_enterprise_reclosures",sa.Column("program_reclosure_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=True,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(48),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("reg_exam_reopened_enterprise_reclosures"); op.drop_table("reg_exam_reopened_enterprise_independent_revalidations"); op.drop_table("reg_exam_reopened_enterprise_intervention_plans")
