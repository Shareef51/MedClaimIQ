"""multimodal reviewer annotations and evidence traceability

Revision ID: 0029_multimodal_reviewer_workbench
Revises: 0028_multimodal_agent_orchestration
"""
from alembic import op
import sqlalchemy as sa
revision="0029_multimodal_reviewer_workbench"
down_revision="0028_multimodal_agent_orchestration"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        "multimodal_review_annotations",
        sa.Column("annotation_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("target_type",sa.String(40),nullable=False),
        sa.Column("target_id",sa.String(180),nullable=False),
        sa.Column("annotation_kind",sa.String(30),nullable=False),
        sa.Column("anchor",sa.JSON(),nullable=False),
        sa.Column("body",sa.Text(),nullable=False),
        sa.Column("body_sha256",sa.String(64),nullable=False),
        sa.Column("tags",sa.JSON(),nullable=False),
        sa.Column("idempotency_key",sa.String(180),nullable=False),
        sa.Column("trace_id",sa.String(128)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_multimodal_review_annotation_idempotency"),
    )
    op.create_index("ix_multimodal_review_annotation_claim","multimodal_review_annotations",["tenant_id","claim_id","created_at"])
    op.create_index("ix_multimodal_review_annotation_target","multimodal_review_annotations",["tenant_id","claim_id","target_type","target_id"])
    op.execute('ALTER TABLE "multimodal_review_annotations" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "multimodal_review_annotations" FORCE ROW LEVEL SECURITY')
    op.execute("CREATE POLICY multimodal_review_annotations_tenant_isolation ON multimodal_review_annotations USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")
    op.execute('CREATE TRIGGER multimodal_review_annotations_immutable BEFORE UPDATE OR DELETE ON "multimodal_review_annotations" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    op.drop_table("multimodal_review_annotations")
