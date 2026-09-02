"""multimodal specialist orchestration investigations and immutable audit events

Revision ID: 0028_multimodal_agent_orchestration
Revises: 0027_multimodal_rag
"""
from alembic import op
import sqlalchemy as sa
revision="0028_multimodal_agent_orchestration"
down_revision="0027_multimodal_rag"
branch_labels=None
depends_on=None
TABLES=("multimodal_agent_investigations","multimodal_agent_events")

def _rls(table):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'CREATE POLICY {table}_tenant_isolation ON "{table}" USING (tenant_id = current_setting(\'app.current_tenant_id\', true)) WITH CHECK (tenant_id = current_setting(\'app.current_tenant_id\', true))')

def upgrade():
    op.create_table("multimodal_agent_investigations",
        sa.Column("investigation_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("workflow_id",sa.String(128),sa.ForeignKey("agent_workflows.workflow_id",ondelete="CASCADE"),nullable=False),
        sa.Column("agent_name",sa.String(80),nullable=False),sa.Column("attempt",sa.Integer(),nullable=False),
        sa.Column("multimodal_run_id",sa.String(128),sa.ForeignKey("multimodal_rag_runs.run_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("pack_id",sa.String(128),sa.ForeignKey("multimodal_evidence_packs.pack_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("pack_sha256",sa.String(64),nullable=False),sa.Column("query_sha256",sa.String(64),nullable=False),
        sa.Column("requested_modalities",sa.JSON(),nullable=False),sa.Column("required_modalities",sa.JSON(),nullable=False),
        sa.Column("answerability",sa.String(30),nullable=False),sa.Column("confidence",sa.Float(),nullable=False),
        sa.Column("material_inconsistency_count",sa.Integer(),nullable=False),sa.Column("blocking_gap_count",sa.Integer(),nullable=False),
        sa.Column("human_review_required",sa.Boolean(),nullable=False),sa.Column("escalation_reasons",sa.JSON(),nullable=False),
        sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_multimodal_agent_investigation_workflow","multimodal_agent_investigations",["tenant_id","workflow_id","created_at"])
    op.create_index("ix_multimodal_agent_investigation_pack","multimodal_agent_investigations",["tenant_id","pack_id"])
    op.create_table("multimodal_agent_events",
        sa.Column("event_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("workflow_id",sa.String(128),sa.ForeignKey("agent_workflows.workflow_id",ondelete="CASCADE"),nullable=False),
        sa.Column("investigation_id",sa.String(128),sa.ForeignKey("multimodal_agent_investigations.investigation_id",ondelete="CASCADE"),nullable=False),
        sa.Column("agent_name",sa.String(80),nullable=False),sa.Column("event_type",sa.String(100),nullable=False),
        sa.Column("event_payload",sa.JSON(),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_multimodal_agent_event_workflow","multimodal_agent_events",["tenant_id","workflow_id","created_at"])
    for table in TABLES:
        _rls(table)
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')

def downgrade():
    for table in reversed(TABLES): op.drop_table(table)
