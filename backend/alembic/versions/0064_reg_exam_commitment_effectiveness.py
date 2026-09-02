"""release 69 regulatory examination commitment effectiveness
Revision ID: 0064_reg_exam_commitment_effectiveness
Revises: 0063_reg_exam_commitment_lifecycle
"""
from alembic import op
import sqlalchemy as sa
revision="0064_reg_exam_commitment_effectiveness"
down_revision="0063_reg_exam_commitment_lifecycle"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("regulatory_exam_commitment_effectiveness_validations",sa.Column("validation_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("validator_user_id",sa.String(128),nullable=False),sa.Column("validator_role",sa.String(64),nullable=False),sa.Column("result",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("scope_entities_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("validated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_closure_versions",sa.Column("closure_version_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("readiness_score",sa.Integer(),nullable=False),sa.Column("blockers_json",sa.JSON(),nullable=False),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("certified_by",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_sustainability_observations",sa.Column("observation_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("days_since_closure",sa.Integer(),nullable=False),sa.Column("health_score",sa.Float(),nullable=False),sa.Column("control_effective",sa.Boolean(),nullable=False),sa.Column("recurrence_detected",sa.Boolean(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_reopen_decisions",sa.Column("reopen_decision_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("decided_by",sa.String(128),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_commitment_reopen_decisions"); op.drop_table("regulatory_exam_commitment_sustainability_observations"); op.drop_table("regulatory_exam_commitment_closure_versions"); op.drop_table("regulatory_exam_commitment_effectiveness_validations")
