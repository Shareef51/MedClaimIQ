"""regulatory examination enterprise intervention sustainability
Revision ID: 0070_reg_exam_enterprise_intervention_sustainability
Revises: 0069_reg_exam_enterprise_intervention_execution
"""
from alembic import op
import sqlalchemy as sa
revision="0070_reg_exam_enterprise_intervention_sustainability"; down_revision="0069_reg_exam_enterprise_intervention_execution"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("regulatory_exam_intervention_sustainability_assurance",sa.Column("sustainability_assurance_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("assessment_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_intervention_residual_risk_acceptance",sa.Column("residual_risk_acceptance_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(48),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("residual_systemic_risk_score",sa.Float(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_intervention_program_closures",sa.Column("program_closure_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(48),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("closure_readiness_score",sa.Float(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_intervention_program_closures"); op.drop_table("regulatory_exam_intervention_residual_risk_acceptance"); op.drop_table("regulatory_exam_intervention_sustainability_assurance")
