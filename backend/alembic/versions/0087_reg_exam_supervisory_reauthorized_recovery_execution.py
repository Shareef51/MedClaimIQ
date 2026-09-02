"""supervisory reauthorized recovery execution and independent recovery assurance
Revision ID: 0087_reg_exam_supervisory_reauthorized_recovery_execution
Revises: 0086_reg_exam_reopened_reauthorized_recovery_investigation
"""
from alembic import op
import sqlalchemy as sa

revision = "0087_reg_exam_supervisory_reauthorized_recovery_execution"
down_revision = "0086_reg_exam_reopened_reauthorized_recovery_investigation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reg_exam_supervisory_reauthorized_recovery_executions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release91_reauthorization_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("release91_investigation_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="active"),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_supervisory_recovery_execution_checkpoints",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("execution_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("checkpoint_type", sa.String(96), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_supervisory_independent_recovery_assurance",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("execution_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("human_reviewer_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_supervisory_recovery_progress_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("execution_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("reg_exam_supervisory_recovery_progress_reviews")
    op.drop_table("reg_exam_supervisory_independent_recovery_assurance")
    op.drop_table("reg_exam_supervisory_recovery_execution_checkpoints")
    op.drop_table("reg_exam_supervisory_reauthorized_recovery_executions")
