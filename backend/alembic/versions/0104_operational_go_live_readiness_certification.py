"""production performance resilience disaster recovery and operational go-live readiness certification
Revision ID: 0104_operational_go_live_readiness_certification
Revises: 0103_release_security_red_team_certification
"""
from alembic import op
import sqlalchemy as sa
revision="0104_operational_go_live_readiness_certification"
down_revision="0103_release_security_red_team_certification"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("release_operational_drill_runs",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=False),sa.Column("release107_release_candidate_decision_version_id",sa.String(64),nullable=False,index=True),sa.Column("release108_release_security_certification_version_id",sa.String(64),nullable=False,index=True),sa.Column("environment",sa.String(64),nullable=False),sa.Column("status",sa.String(32),nullable=False,server_default="evaluated"),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_operational_evidence_packs",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("operational_drill_run_id",sa.String(64),nullable=False,index=True),sa.Column("evidence_pack_hash",sa.String(64),nullable=False,index=True),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("release_operational_readiness_certifications",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=False),sa.Column("release107_release_candidate_decision_version_id",sa.String(64),nullable=False,index=True),sa.Column("release108_release_security_certification_version_id",sa.String(64),nullable=False,index=True),sa.Column("operational_drill_run_id",sa.String(64),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("release_operational_readiness_certifications"); op.drop_table("release_operational_evidence_packs"); op.drop_table("release_operational_drill_runs")
