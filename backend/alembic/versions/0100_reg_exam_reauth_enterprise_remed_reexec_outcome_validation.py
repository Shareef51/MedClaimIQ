"""production regulatory examination reauthorized enterprise remediation re-execution outcome validation, systemic recovery recertification and sustainability reclosure assurance
Revision ID: 0100_reg_exam_reauth_enterprise_remed_reexec_outcome_validation
Revises: 0099_reg_exam_reauthorized_enterprise_remediation_reexecution
"""
from alembic import op
import sqlalchemy as sa

revision = "0100_reg_exam_reauth_enterprise_remed_reexec_outcome_validation"
down_revision = "0099_reg_exam_reauthorized_enterprise_remediation_reexecution"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reg_exam_reauth_enterprise_remed_reexec_outcome_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("record_type", sa.String(80), nullable=False),
        sa.Column("release104_reexecution_version_id", sa.String(128), nullable=True),
        sa.Column("release104_assurance_version_id", sa.String(128), nullable=True),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reauth_enterprise_remed_reexec_sustainability_obs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("entity_id", sa.String(128), nullable=True, index=True),
        sa.Column("control_health_score", sa.Float(), nullable=True),
        sa.Column("breach", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reauth_enterprise_remed_reexec_recert_reclosures",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("decision_type", sa.String(64), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("reg_exam_reauth_enterprise_remed_reexec_recert_reclosures")
    op.drop_table("reg_exam_reauth_enterprise_remed_reexec_sustainability_obs")
    op.drop_table("reg_exam_reauth_enterprise_remed_reexec_outcome_versions")
