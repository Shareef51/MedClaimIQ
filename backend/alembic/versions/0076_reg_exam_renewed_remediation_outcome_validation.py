"""renewed remediation outcome validation
Revision ID: 0076_reg_exam_renewed_remediation_outcome_validation
Revises: 0075_reg_exam_renewed_enterprise_remediation_execution
"""
from alembic import op
import sqlalchemy as sa
revision="0076_reg_exam_renewed_remediation_outcome_validation"
down_revision="0075_reg_exam_renewed_enterprise_remediation_execution"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("reg_exam_renewed_remediation_outcome_versions",
        sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),
        sa.Column("record_type",sa.String(80),nullable=False),sa.Column("record_id",sa.String(128),nullable=False,index=True),
        sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_reg_exam_renewed_outcome_tenant_record","reg_exam_renewed_remediation_outcome_versions",["tenant_id","record_id"])

def downgrade():
    op.drop_index("ix_reg_exam_renewed_outcome_tenant_record",table_name="reg_exam_renewed_remediation_outcome_versions")
    op.drop_table("reg_exam_renewed_remediation_outcome_versions")
