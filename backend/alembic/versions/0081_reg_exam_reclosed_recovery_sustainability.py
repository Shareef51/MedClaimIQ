"""reclosed recovery sustainability monitoring and multi-cycle supervisory escalation
Revision ID: 0081_reg_exam_reclosed_recovery_sustainability
Revises: 0080_reg_exam_renewed_recovery_outcome_validation
"""
from alembic import op
import sqlalchemy as sa
revision="0081_reg_exam_reclosed_recovery_sustainability"
down_revision="0080_reg_exam_renewed_recovery_outcome_validation"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("reg_exam_reclosed_recovery_surveillance_versions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("program_id",sa.String(128),nullable=False,index=True),sa.Column("record_type",sa.String(80),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_reg_exam_reclosed_recovery_surveillance_tenant_program","reg_exam_reclosed_recovery_surveillance_versions",["tenant_id","program_id"])
    op.create_table("reg_exam_multi_cycle_recovery_investigations",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("program_id",sa.String(128),nullable=False,index=True),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("materiality_score",sa.Float(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("reg_exam_multi_cycle_recovery_escalation_versions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("program_id",sa.String(128),nullable=False,index=True),sa.Column("investigation_id",sa.String(64),nullable=False),sa.Column("escalation_tier",sa.Integer(),nullable=False),sa.Column("human_actor_id",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table("reg_exam_multi_cycle_recovery_escalation_versions"); op.drop_table("reg_exam_multi_cycle_recovery_investigations"); op.drop_index("ix_reg_exam_reclosed_recovery_surveillance_tenant_program",table_name="reg_exam_reclosed_recovery_surveillance_versions"); op.drop_table("reg_exam_reclosed_recovery_surveillance_versions")
