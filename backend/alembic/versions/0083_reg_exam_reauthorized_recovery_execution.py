"""reauthorized recovery execution and independent recovery assurance
Revision ID: 0083_reg_exam_reauthorized_recovery_execution
Revises: 0082_reg_exam_repeated_recovery_failure_investigation
"""
from alembic import op
import sqlalchemy as sa
revision="0083_reg_exam_reauthorized_recovery_execution"; down_revision="0082_reg_exam_repeated_recovery_failure_investigation"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("reg_exam_reauthorized_recovery_executions",sa.Column("reauthorized_recovery_execution_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("remediation_reauthorization_version_id",sa.String(36),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reauthorized_control_rerehabilitation_events",sa.Column("control_rerehabilitation_event_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_independent_recovery_assurance",sa.Column("independent_recovery_assurance_version_id",sa.String(36),primary_key=True),sa.Column("recovery_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("reg_exam_independent_recovery_assurance"); op.drop_table("reg_exam_reauthorized_control_rerehabilitation_events"); op.drop_table("reg_exam_reauthorized_recovery_executions")
