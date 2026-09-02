"""production end-to-end integration, cross-domain regression and release candidate hardening
Revision ID: 0102_release_candidate_hardening
Revises: 0101_reg_exam_reclosed_reauth_ent_remed_reexec_surveillance
"""
from alembic import op
import sqlalchemy as sa
revision="0102_release_candidate_hardening"
down_revision="0101_reg_exam_reclosed_reauth_ent_remed_reexec_surveillance"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("release_candidate_integration_runs",
        sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=False),sa.Column("git_sha",sa.String(128),nullable=False),sa.Column("status",sa.String(32),nullable=False,server_default="evaluated"),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_candidate_gate_assessments",
        sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("integration_run_id",sa.String(64),nullable=False,index=True),sa.Column("gate_name",sa.String(128),nullable=False,index=True),sa.Column("passed",sa.Boolean(),nullable=False),sa.Column("evidence",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_candidate_human_decisions",
        sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("integration_run_id",sa.String(64),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("release_candidate_human_decisions"); op.drop_table("release_candidate_gate_assessments"); op.drop_table("release_candidate_integration_runs")
