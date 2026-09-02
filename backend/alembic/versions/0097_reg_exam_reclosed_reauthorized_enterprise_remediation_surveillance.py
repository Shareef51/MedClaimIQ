"""reclosed reauthorized enterprise remediation surveillance and enterprise reopening governance
Revision ID: 0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance
Revises: 0096_reg_exam_reauthorized_enterprise_remediation_outcome_validation
"""
from alembic import op
import sqlalchemy as sa

revision = "0097_reg_exam_reclosed_reauthorized_enterprise_remediation_surveillance"
down_revision = "0096_reg_exam_reauthorized_enterprise_remediation_outcome_validation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reg_exam_reclosed_reauth_ent_remediation_surveillance_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("record_type", sa.String(80), nullable=False),
        sa.Column("release101_reclosure_version_id", sa.String(64), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reauth_ent_remediation_decay_investigations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release101_reclosure_version_id", sa.String(64), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="open"),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reauth_ent_remediation_reopening_decisions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release101_reclosure_version_id", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("reg_exam_reauth_ent_remediation_reopening_decisions")
    op.drop_table("reg_exam_reauth_ent_remediation_decay_investigations")
    op.drop_table("reg_exam_reclosed_reauth_ent_remediation_surveillance_versions")
