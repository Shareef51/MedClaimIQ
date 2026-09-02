"""regulatory examination reclosed intervention sustainability
Revision ID: 0073_reg_exam_reclosed_intervention_sustainability
Revises: 0072_reg_exam_reopened_enterprise_intervention
"""
from alembic import op
import sqlalchemy as sa
revision="0073_reg_exam_reclosed_intervention_sustainability"; down_revision="0072_reg_exam_reopened_enterprise_intervention"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("reg_exam_reclosed_intervention_surveillance",sa.Column("surveillance_observation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reclosure_version_id",sa.String(36),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reclosed_intervention_escalations",sa.Column("supervisory_escalation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("escalation_tier",sa.String(32),nullable=False),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reclosed_intervention_investigations",sa.Column("supervisory_investigation_version_id",sa.String(36),primary_key=True),sa.Column("intervention_program_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("payload_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("reg_exam_reclosed_intervention_investigations"); op.drop_table("reg_exam_reclosed_intervention_escalations"); op.drop_table("reg_exam_reclosed_intervention_surveillance")
