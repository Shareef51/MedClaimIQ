"""regulatory examination systemic failure investigation
Revision ID: 0074_reg_exam_systemic_failure_investigation
Revises: 0073_reg_exam_reclosed_intervention_sustainability
"""
from alembic import op
import sqlalchemy as sa
revision="0074_reg_exam_systemic_failure_investigation"; down_revision="0073_reg_exam_reclosed_intervention_sustainability"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("reg_exam_systemic_failure_investigations",sa.Column("systemic_failure_investigation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_systemic_failure_reauthorization",sa.Column("remediation_reauthorization_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_systemic_failure_conclusions",sa.Column("investigation_conclusion_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("reg_exam_systemic_failure_conclusions"); op.drop_table("reg_exam_systemic_failure_reauthorization"); op.drop_table("reg_exam_systemic_failure_investigations")
