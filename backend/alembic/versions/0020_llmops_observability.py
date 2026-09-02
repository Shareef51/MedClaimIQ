"""LLMOps usage ledger and SLO event persistence.
Revision ID: 0020_llmops_observability
Revises: 0019_ai_evaluation_quality
"""
from alembic import op
import sqlalchemy as sa
revision="0020_llmops_observability"; down_revision="0019_ai_evaluation_quality"; branch_labels=None; depends_on=None
TABLES=("ai_usage_ledger","ai_slo_events")
def _rls(t):
    op.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{t}" FORCE ROW LEVEL SECURITY')
    op.execute(f'CREATE POLICY {t}_tenant_isolation ON "{t}" USING (tenant_id = current_setting(\'app.current_tenant_id\', true)) WITH CHECK (tenant_id = current_setting(\'app.current_tenant_id\', true))')
def upgrade():
    op.create_table("ai_usage_ledger",
        sa.Column("usage_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="SET NULL")),sa.Column("workflow_id",sa.String(128)),
        sa.Column("trace_id",sa.String(64)),sa.Column("span_id",sa.String(32)),sa.Column("operation_kind",sa.String(40),nullable=False),
        sa.Column("provider",sa.String(60),nullable=False),sa.Column("model_name",sa.String(160),nullable=False),sa.Column("prompt_key",sa.String(160)),
        sa.Column("prompt_version",sa.String(80)),sa.Column("prompt_sha256",sa.String(64)),sa.Column("input_tokens",sa.Integer()),sa.Column("output_tokens",sa.Integer()),
        sa.Column("estimated_cost_usd",sa.Float()),sa.Column("pricing_version",sa.String(80),nullable=False),sa.Column("latency_ms",sa.Float()),sa.Column("status",sa.String(30),nullable=False),
        sa.Column("metadata",sa.JSON(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_ai_usage_tenant_created","ai_usage_ledger",["tenant_id","created_at"]); op.create_index("ix_ai_usage_trace","ai_usage_ledger",["tenant_id","trace_id","created_at"])
    op.create_table("ai_slo_events",
        sa.Column("slo_event_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("slo_kind",sa.String(80),nullable=False),sa.Column("dedupe_key",sa.String(160),nullable=False),sa.Column("severity",sa.String(20),nullable=False),sa.Column("observed_value",sa.Float(),nullable=False),
        sa.Column("threshold_value",sa.Float(),nullable=False),sa.Column("window_minutes",sa.Integer(),nullable=False),sa.Column("trace_id",sa.String(64)),sa.Column("details",sa.JSON(),nullable=False),
        sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_ai_slo_tenant_created","ai_slo_events",["tenant_id","created_at"]); op.create_unique_constraint("uq_ai_slo_dedupe","ai_slo_events",["tenant_id","dedupe_key"])
    for t in TABLES:_rls(t)
    for t in TABLES: op.execute(f'CREATE TRIGGER {t}_immutable BEFORE UPDATE OR DELETE ON "{t}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')
def downgrade():
    for t in reversed(TABLES): op.drop_table(t)
