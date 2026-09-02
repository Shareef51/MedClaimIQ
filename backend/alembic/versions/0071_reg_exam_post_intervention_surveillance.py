"""regulatory examination post intervention surveillance
Revision ID: 0071_reg_exam_post_intervention_surveillance
Revises: 0070_reg_exam_enterprise_intervention_sustainability
"""
from alembic import op
import sqlalchemy as sa
revision="0071_reg_exam_post_intervention_surveillance"; down_revision="0070_reg_exam_enterprise_intervention_sustainability"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("regulatory_exam_post_intervention_investigations",sa.Column("recurrence_investigation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("prior_closure_version_id",sa.String(36),nullable=False),sa.Column("prior_residual_risk_acceptance_version_id",sa.String(36),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_post_intervention_reassessments",sa.Column("independent_reassessment_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_intervention_program_reopenings",sa.Column("program_reopening_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(48),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_intervention_program_reopenings"); op.drop_table("regulatory_exam_post_intervention_reassessments"); op.drop_table("regulatory_exam_post_intervention_investigations")
