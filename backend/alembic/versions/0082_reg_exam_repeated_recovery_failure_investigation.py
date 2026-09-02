"""repeated recovery failure investigation and remediation reauthorization
Revision ID: 0082_reg_exam_repeated_recovery_failure_investigation
Revises: 0081_reg_exam_reclosed_recovery_sustainability
"""
from alembic import op
import sqlalchemy as sa
revision="0082_reg_exam_repeated_recovery_failure_investigation"; down_revision="0081_reg_exam_reclosed_recovery_sustainability"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("reg_exam_repeated_recovery_failure_investigations",sa.Column("repeated_recovery_failure_investigation_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_recovery_remediation_reauthorizations",sa.Column("recovery_remediation_reauthorization_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_recovery_investigation_conclusions",sa.Column("recovery_investigation_conclusion_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("reg_exam_recovery_investigation_conclusions"); op.drop_table("reg_exam_recovery_remediation_reauthorizations"); op.drop_table("reg_exam_repeated_recovery_failure_investigations")
