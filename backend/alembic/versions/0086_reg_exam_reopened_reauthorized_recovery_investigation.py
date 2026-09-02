"""reopened reauthorized recovery investigation and supervisory recovery reauthorization
Revision ID: 0086_reg_exam_reopened_reauthorized_recovery_investigation
Revises: 0085_reg_exam_reclosed_reauthorized_recovery_surveillance
"""
from alembic import op
import sqlalchemy as sa

revision = "0086_reg_exam_reopened_reauthorized_recovery_investigation"
down_revision = "0085_reg_exam_reclosed_reauthorized_recovery_surveillance"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "reg_exam_reopened_reauthorized_recovery_investigations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("release90_reopening_version_id", sa.String(64), nullable=False, index=True),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="open"),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_reopened_recovery_investigation_conclusions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("investigation_id", sa.String(64), nullable=False, index=True),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "reg_exam_supervisory_recovery_reauthorizations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("recovery_program_id", sa.String(128), nullable=False, index=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("human_actor_id", sa.String(128), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade():
    op.drop_table("reg_exam_supervisory_recovery_reauthorizations")
    op.drop_table("reg_exam_reopened_recovery_investigation_conclusions")
    op.drop_table("reg_exam_reopened_reauthorized_recovery_investigations")
