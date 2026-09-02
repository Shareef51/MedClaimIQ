"""final production go-live governance and certification
Revision ID: 0105_final_production_go_live
Revises: 0104_operational_go_live_readiness_certification
"""
from alembic import op
import sqlalchemy as sa
revision="0105_final_production_go_live"
down_revision="0104_operational_go_live_readiness_certification"
branch_labels=None
depends_on=None

def _common(name):
    return op.create_table(name,sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("release_id",sa.String(128),nullable=False,index=True),sa.Column("candidate_version",sa.String(128),nullable=True),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def upgrade():
    _common("release_final_manifests"); _common("release_go_live_approvals"); _common("release_deployment_verifications"); _common("release_final_certifications"); _common("release_hypercare_checkpoints"); _common("release_hypercare_closures")
def downgrade():
    for x in ["release_hypercare_closures","release_hypercare_checkpoints","release_final_certifications","release_deployment_verifications","release_go_live_approvals","release_final_manifests"]: op.drop_table(x)
