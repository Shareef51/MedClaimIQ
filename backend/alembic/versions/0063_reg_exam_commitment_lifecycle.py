"""release 68 regulatory examination commitment lifecycle
Revision ID: 0063_reg_exam_commitment_lifecycle
Revises: 0062_reg_exam_interaction
"""
from alembic import op
import sqlalchemy as sa
revision="0063_reg_exam_commitment_lifecycle"
down_revision="0062_reg_exam_interaction"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("regulatory_exam_commitment_versions",sa.Column("version_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("examination_id",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("owner_user_id",sa.String(128),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("source_type",sa.String(32),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_by",sa.String(128),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_milestones",sa.Column("milestone_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("title",sa.Text(),nullable=False),sa.Column("owner_user_id",sa.String(128),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("dependency_ids_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_evidence_links",sa.Column("link_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("milestone_id",sa.String(36)),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("evidence_id",sa.String(128),nullable=False),sa.Column("evidence_type",sa.String(64),nullable=False),sa.Column("evidence_version_id",sa.String(128),nullable=False),sa.Column("sha256",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_certifications",sa.Column("certification_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(32),nullable=False),sa.Column("reviewer_role",sa.String(64),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("certified_by",sa.String(128),nullable=False),sa.Column("certified_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitment_follow_ups",sa.Column("follow_up_id",sa.String(36),primary_key=True),sa.Column("commitment_id",sa.String(36),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("examination_id",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("regulator_reference",sa.String(256)),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_commitment_follow_ups"); op.drop_table("regulatory_exam_commitment_certifications"); op.drop_table("regulatory_exam_commitment_evidence_links"); op.drop_table("regulatory_exam_commitment_milestones"); op.drop_table("regulatory_exam_commitment_versions")
