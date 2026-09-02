"""reauthorized enterprise remediation re-execution and independent recovery effectiveness assurance
Revision ID: 0099_reg_exam_reauthorized_enterprise_remediation_reexecution
Revises: 0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0099_reg_exam_reauthorized_enterprise_remediation_reexecution"
down_revision="0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("reg_exam_reauthorized_enterprise_remediation_reexecution_versions",sa.Column("id",sa.String(length=64),primary_key=True),sa.Column("tenant_id",sa.String(length=128),nullable=False),sa.Column("remediation_program_id",sa.String(length=128),nullable=False),sa.Column("record_type",sa.String(length=96),nullable=False),sa.Column("version_hash",sa.String(length=64),nullable=False),sa.Column("payload",postgresql.JSONB(astext_type=sa.Text()),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_reg_exam_reauth_enterprise_remed_reexec_tenant_program","reg_exam_reauthorized_enterprise_remediation_reexecution_versions",["tenant_id","remediation_program_id"])
def downgrade():
    op.drop_index("ix_reg_exam_reauth_enterprise_remed_reexec_tenant_program",table_name="reg_exam_reauthorized_enterprise_remediation_reexecution_versions")
    op.drop_table("reg_exam_reauthorized_enterprise_remediation_reexecution_versions")
