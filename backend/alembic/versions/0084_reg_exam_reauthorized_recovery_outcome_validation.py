"""reauthorized recovery outcome validation, recertification and sustainability reclosure
Revision ID: 0084_reg_exam_reauthorized_recovery_outcome_validation
Revises: 0083_reg_exam_reauthorized_recovery_execution
"""
from alembic import op
import sqlalchemy as sa
revision="0084_reg_exam_reauthorized_recovery_outcome_validation"
down_revision="0083_reg_exam_reauthorized_recovery_execution"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("reg_exam_reauthorized_recovery_outcome_versions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("recovery_program_id",sa.String(128),nullable=False,index=True),sa.Column("record_type",sa.String(80),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reauthorized_recovery_sustainability_observations",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("recovery_program_id",sa.String(128),nullable=False,index=True),sa.Column("control_health_score",sa.Float(),nullable=True),sa.Column("breach",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("observed_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_reauthorized_recovery_recertification_reclosures",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("recovery_program_id",sa.String(128),nullable=False,index=True),sa.Column("decision_type",sa.String(64),nullable=False),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("reg_exam_reauthorized_recovery_recertification_reclosures"); op.drop_table("reg_exam_reauthorized_recovery_sustainability_observations"); op.drop_table("reg_exam_reauthorized_recovery_outcome_versions")
