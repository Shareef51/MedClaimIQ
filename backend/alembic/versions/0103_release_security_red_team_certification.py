"""production security privacy compliance red-team and release security certification
Revision ID: 0103_release_security_red_team_certification
Revises: 0102_release_candidate_hardening
"""
from alembic import op
import sqlalchemy as sa
revision="0103_release_security_red_team_certification"
down_revision="0102_release_candidate_hardening"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("release_security_red_team_runs",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=False),sa.Column("release107_release_candidate_decision_version_id",sa.String(64),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False,server_default="evaluated"),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_security_findings",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("red_team_run_id",sa.String(64),nullable=False,index=True),sa.Column("finding_id",sa.String(128),nullable=False,index=True),sa.Column("severity",sa.String(16),nullable=False,index=True),sa.Column("category",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("non_waivable",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_security_waivers",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("finding_id",sa.String(128),nullable=False,index=True),sa.Column("approved_by",sa.String(128),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_security_certifications",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=False),sa.Column("release107_release_candidate_decision_version_id",sa.String(64),nullable=False,index=True),sa.Column("red_team_run_id",sa.String(64),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("release_security_certifications"); op.drop_table("release_security_waivers"); op.drop_table("release_security_findings"); op.drop_table("release_security_red_team_runs")
