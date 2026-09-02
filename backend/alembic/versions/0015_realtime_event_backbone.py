"""Real-time event backbone, consumer deduplication, DLQ and replay

Revision ID: 0015_realtime_event_backbone
Revises: 0014_mcp_tool_control_plane
"""
from alembic import op
import sqlalchemy as sa

revision="0015_realtime_event_backbone"
down_revision="0014_mcp_tool_control_plane"
branch_labels=None
depends_on=None
TABLES=("realtime_outbox","event_consumer_receipts","event_dead_letters","event_replay_requests","realtime_stream_events")
IMMUTABLE=("event_consumer_receipts","event_dead_letters","realtime_stream_events")

def _rls(table):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'''CREATE POLICY {table}_tenant_isolation ON "{table}" USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))''')

def upgrade():
    op.create_table("realtime_outbox",
        sa.Column("outbox_id",sa.String(128),primary_key=True), sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=True), sa.Column("event_id",sa.String(128),nullable=False),
        sa.Column("event_type",sa.String(140),nullable=False), sa.Column("event_version",sa.String(20),nullable=False), sa.Column("topic",sa.String(180),nullable=False),
        sa.Column("partition_key",sa.String(180),nullable=False), sa.Column("envelope",sa.JSON(),nullable=False), sa.Column("status",sa.String(30),nullable=False),
        sa.Column("attempt_count",sa.Integer(),nullable=False,server_default="0"), sa.Column("available_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("claimed_at",sa.DateTime(timezone=True)), sa.Column("published_at",sa.DateTime(timezone=True)), sa.Column("last_error_code",sa.String(100)),
        sa.Column("last_error_detail",sa.Text()), sa.Column("created_at",sa.DateTime(timezone=True),nullable=False), sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("event_id",name="uq_realtime_outbox_event"))
    op.create_index("ix_realtime_outbox_dispatch","realtime_outbox",["status","available_at","created_at"])
    op.create_index("ix_realtime_outbox_tenant_claim","realtime_outbox",["tenant_id","claim_id","created_at"])
    op.create_table("event_consumer_receipts",
        sa.Column("receipt_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE")),sa.Column("event_id",sa.String(128),nullable=False),sa.Column("consumer_group",sa.String(160),nullable=False),
        sa.Column("topic",sa.String(180),nullable=False),sa.Column("partition",sa.Integer()),sa.Column("offset",sa.Integer()),sa.Column("status",sa.String(30),nullable=False),sa.Column("attempt_count",sa.Integer(),nullable=False),sa.Column("processed_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("consumer_group","event_id",name="uq_consumer_event_once"))
    op.create_index("ix_consumer_receipt_tenant_claim","event_consumer_receipts",["tenant_id","claim_id","processed_at"])
    op.create_table("event_dead_letters",
        sa.Column("dead_letter_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE")),
        sa.Column("event_id",sa.String(128),nullable=False),sa.Column("source_topic",sa.String(180),nullable=False),sa.Column("consumer_group",sa.String(160),nullable=False),sa.Column("attempt_count",sa.Integer(),nullable=False),sa.Column("envelope_sha256",sa.String(64),nullable=False),sa.Column("replay_envelope",sa.JSON(),nullable=False),sa.Column("error_code",sa.String(100),nullable=False),sa.Column("error_detail_sha256",sa.String(64),nullable=False),sa.Column("replayed",sa.Boolean(),nullable=False,server_default=sa.text("false")),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("replayed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_event_dlq_tenant_claim","event_dead_letters",["tenant_id","claim_id","created_at"])
    op.create_table("event_replay_requests",
        sa.Column("replay_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE")),sa.Column("dead_letter_id",sa.String(128),sa.ForeignKey("event_dead_letters.dead_letter_id",ondelete="RESTRICT"),nullable=False),sa.Column("requested_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("reason_sha256",sa.String(64),nullable=False),sa.Column("target_topic",sa.String(180),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("executed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_event_replay_tenant_status","event_replay_requests",["tenant_id","status","created_at"])
    op.create_table("realtime_stream_events",
        sa.Column("stream_sequence",sa.Integer(),primary_key=True,autoincrement=True),sa.Column("event_id",sa.String(128),nullable=False),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE")),sa.Column("topic",sa.String(180),nullable=False),sa.Column("event_type",sa.String(140),nullable=False),sa.Column("event_version",sa.String(20),nullable=False),sa.Column("envelope_sha256",sa.String(64),nullable=False),sa.Column("stream_payload",sa.JSON(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("published_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("event_id",name="uq_realtime_stream_event"))
    op.create_index("ix_realtime_stream_claim","realtime_stream_events",["tenant_id","claim_id","stream_sequence"])
    for table in TABLES: _rls(table)
    for table in IMMUTABLE:
        op.execute(f'''CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()''')

def downgrade():
    for table in reversed(TABLES): op.drop_table(table)
