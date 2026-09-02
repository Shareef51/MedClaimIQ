"""regulatory examination readiness operations and evidence rooms
Revision ID: 0060_reg_examination_readiness_operations
Revises: 0059_reg_enterprise_knowledge_governance
"""
from alembic import op
import sqlalchemy as sa
revision = "0060_reg_examination_readiness_operations"
down_revision = "0059_reg_enterprise_knowledge_governance"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("regulatory_examination_scopes",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("examination_id", sa.String(128), nullable=False), sa.Column("regulator", sa.String(255), nullable=False),
        sa.Column("scope_json", sa.JSON, nullable=False), sa.Column("owner_id", sa.String(128), nullable=False),
        sa.UniqueConstraint("tenant_id", "examination_id", name="uq_reg_exam_scope"))
    op.create_table("regulatory_exam_requests",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("examination_id", sa.String(128), nullable=False), sa.Column("external_request_ref", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False), sa.Column("request_json", sa.JSON, nullable=False),
        sa.UniqueConstraint("tenant_id", "examination_id", "external_request_ref", name="uq_reg_exam_request_ref"))
    op.create_table("regulatory_exam_evidence_map",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("request_id", sa.String(64), nullable=False), sa.Column("evidence_id", sa.String(128), nullable=False),
        sa.Column("evidence_class", sa.String(32), nullable=False), sa.Column("version_id", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("citation_anchor", sa.String(512), nullable=False),
        sa.Column("mapping_json", sa.JSON, nullable=False),
        sa.UniqueConstraint("tenant_id", "request_id", "evidence_id", "version_id", name="uq_reg_exam_evidence_version"))
    op.create_table("regulatory_exam_response_versions",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("request_id", sa.String(64), nullable=False), sa.Column("version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("response_json", sa.JSON, nullable=False),
        sa.Column("approved_by", sa.String(128)),
        sa.UniqueConstraint("tenant_id", "request_id", "version", name="uq_reg_exam_response_version"))
    op.create_table("regulatory_exam_submission_packages",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("examination_id", sa.String(128), nullable=False), sa.Column("version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(48), nullable=False), sa.Column("manifest_hash", sa.String(64), nullable=False),
        sa.Column("manifest_json", sa.JSON, nullable=False), sa.Column("approved_by", sa.String(128)),
        sa.UniqueConstraint("tenant_id", "examination_id", "version", name="uq_reg_exam_submission_package_version"))

def downgrade():
    op.drop_table("regulatory_exam_submission_packages")
    op.drop_table("regulatory_exam_response_versions")
    op.drop_table("regulatory_exam_evidence_map")
    op.drop_table("regulatory_exam_requests")
    op.drop_table("regulatory_examination_scopes")
