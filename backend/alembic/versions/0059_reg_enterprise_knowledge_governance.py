"""enterprise regulatory knowledge governance
Revision ID: 0059_reg_enterprise_knowledge_governance
Revises: 0058_reg_lessons_learned
"""
from alembic import op
import sqlalchemy as sa
revision = "0059_reg_enterprise_knowledge_governance"
down_revision = "0058_reg_lessons_learned"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("regulatory_knowledge_nodes",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("canonical_key", sa.String(255), nullable=False), sa.Column("node_type", sa.String(64), nullable=False),
        sa.Column("knowledge_class", sa.String(32), nullable=False), sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("evidence_refs_json", sa.JSON, nullable=False),
        sa.UniqueConstraint("tenant_id", "canonical_key", "version", name="uq_reg_knowledge_node_version"))
    op.create_table("regulatory_knowledge_edges",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("source_key", sa.String(255), nullable=False), sa.Column("target_key", sa.String(255), nullable=False),
        sa.Column("edge_type", sa.String(64), nullable=False), sa.Column("evidence_refs_json", sa.JSON, nullable=False))
    op.create_table("regulatory_knowledge_releases",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("release_name", sa.String(255), nullable=False), sa.Column("release_version", sa.Integer, nullable=False),
        sa.Column("release_hash", sa.String(64), nullable=False), sa.Column("manifest_json", sa.JSON, nullable=False),
        sa.UniqueConstraint("tenant_id", "release_name", "release_version", name="uq_reg_knowledge_release_version"))

def downgrade():
    op.drop_table("regulatory_knowledge_releases"); op.drop_table("regulatory_knowledge_edges"); op.drop_table("regulatory_knowledge_nodes")
