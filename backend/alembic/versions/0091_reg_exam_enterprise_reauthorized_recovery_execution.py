"""enterprise reauthorized recovery execution and effectiveness assurance

Revision ID: 0091_reg_exam_enterprise_reauthorized_recovery_execution
Revises: 0090_reg_exam_reopened_supervisory_recovery_investigation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0091_reg_exam_enterprise_reauthorized_recovery_execution"
down_revision = "0090_reg_exam_reopened_supervisory_recovery_investigation"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "reg_exam_enterprise_reauthorized_recovery_execution_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("recovery_program_id", sa.String(length=128), nullable=False),
        sa.Column("record_type", sa.String(length=96), nullable=False),
        sa.Column("version_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_reg_exam_enterprise_reauth_recovery_exec_tenant_program",
        "reg_exam_enterprise_reauthorized_recovery_execution_versions",
        ["tenant_id", "recovery_program_id"],
    )

def downgrade():
    op.drop_index("ix_reg_exam_enterprise_reauth_recovery_exec_tenant_program", table_name="reg_exam_enterprise_reauthorized_recovery_execution_versions")
    op.drop_table("reg_exam_enterprise_reauthorized_recovery_execution_versions")
