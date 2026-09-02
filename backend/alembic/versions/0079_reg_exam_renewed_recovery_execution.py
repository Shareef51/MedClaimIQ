"""renewed recovery program execution and independent recovery revalidation
Revision ID: 0079_reg_exam_renewed_recovery_execution
Revises: 0078_reg_exam_reopened_recovery_investigation
"""
from alembic import op
import sqlalchemy as sa
revision="0079_reg_exam_renewed_recovery_execution"
down_revision="0078_reg_exam_reopened_recovery_investigation"
branch_labels=None
depends_on=None
def upgrade():
 op.create_table("reg_exam_renewed_recovery_execution_versions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("program_id",sa.String(128),nullable=False,index=True),sa.Column("record_type",sa.String(80),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
 op.create_index("ix_reg_exam_renewed_recovery_exec_tenant_program","reg_exam_renewed_recovery_execution_versions",["tenant_id","program_id"])
def downgrade():
 op.drop_index("ix_reg_exam_renewed_recovery_exec_tenant_program",table_name="reg_exam_renewed_recovery_execution_versions"); op.drop_table("reg_exam_renewed_recovery_execution_versions")
