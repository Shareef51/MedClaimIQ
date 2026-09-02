"""regulatory examination post commitment surveillance
Revision ID: 0065_reg_exam_post_commitment_surveillance
Revises: 0064_reg_exam_commitment_effectiveness
"""
from alembic import op
import sqlalchemy as sa
revision="0065_reg_exam_post_commitment_surveillance"
down_revision="0064_reg_exam_commitment_effectiveness"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("regulatory_exam_post_commitment_observations",sa.Column("observation_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("health_score",sa.Float(),nullable=False),sa.Column("control_effective",sa.Boolean(),nullable=False),sa.Column("recurrence_detected",sa.Boolean(),nullable=False),sa.Column("entity_id",sa.String(128),nullable=True),sa.Column("examination_id",sa.String(128),nullable=True),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_recurrence_investigations",sa.Column("investigation_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("trigger_type",sa.String(64),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("matched_finding_ids_json",sa.JSON(),nullable=False),sa.Column("affected_entity_ids_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_recurrence_reassessments",sa.Column("reassessment_id",sa.String(36),primary_key=True),sa.Column("investigation_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("result",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_reopening_versions",sa.Column("reopen_version_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("investigation_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("decided_by",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_commitment_reopening_versions"); op.drop_table("regulatory_exam_recurrence_reassessments"); op.drop_table("regulatory_exam_recurrence_investigations"); op.drop_table("regulatory_exam_post_commitment_observations")
