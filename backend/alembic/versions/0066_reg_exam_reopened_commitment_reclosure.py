"""regulatory examination reopened commitment reclosure assurance
Revision ID: 0066_reg_exam_reopened_commitment_reclosure
Revises: 0065_reg_exam_post_commitment_surveillance
"""
from alembic import op
import sqlalchemy as sa
revision="0066_reg_exam_reopened_commitment_reclosure"
down_revision="0065_reg_exam_post_commitment_surveillance"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("regulatory_exam_reopened_remediation_plans",sa.Column("plan_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("investigation_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("owner_user_id",sa.String(128),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("affected_entity_ids_json",sa.JSON(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_reopened_independent_retests",sa.Column("retest_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("result",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("scope_entity_ids_json",sa.JSON(),nullable=False),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_recertifications",sa.Column("recertification_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("decided_by",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_reclosure_versions",sa.Column("reclosure_version_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("recertification_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("sustainability_window_json",sa.JSON(),nullable=False),sa.Column("decided_by",sa.String(128),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_commitment_reclosure_versions"); op.drop_table("regulatory_exam_commitment_recertifications"); op.drop_table("regulatory_exam_reopened_independent_retests"); op.drop_table("regulatory_exam_reopened_remediation_plans")
