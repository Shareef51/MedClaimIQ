"""reopened reauthorized enterprise remediation investigation

Revision ID: 0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation
Revises: 0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance
"""
from alembic import op
import sqlalchemy as sa

revision = "0098_reg_exam_reopened_reauthorized_enterprise_remediation_investigation"
down_revision = "0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reg_exam_reopened_reauthorized_remediation_investigations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release102_enterprise_recovery_reopening_version_id", sa.String(64), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_systemic_remediation_failure_root_cause_confirmations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("investigation_version_id", sa.String(64), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_systemic_remediation_failure_classifications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("classification", sa.String(64), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reopened_reauthorized_remediation_reauthorizations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release102_enterprise_recovery_reopening_version_id", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("reg_exam_reopened_reauthorized_remediation_reauthorizations")
    op.drop_table("reg_exam_systemic_remediation_failure_classifications")
    op.drop_table("reg_exam_systemic_remediation_failure_root_cause_confirmations")
    op.drop_table("reg_exam_reopened_reauthorized_remediation_investigations")
