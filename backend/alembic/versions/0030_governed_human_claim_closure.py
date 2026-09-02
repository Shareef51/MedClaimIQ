"""governed human decision packets, dual-control and adjudication audit

Revision ID: 0030_governed_human_claim_closure
Revises: 0029_multimodal_reviewer_workbench
"""
from alembic import op
import sqlalchemy as sa

revision="0030_governed_human_claim_closure"
down_revision="0029_multimodal_reviewer_workbench"
branch_labels=None
depends_on=None


def _tenant_rls(table: str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")


def upgrade():
    op.create_table(
        "review_decision_packets",
        sa.Column("packet_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("primary_reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("second_reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),
        sa.Column("status",sa.String(40),nullable=False),sa.Column("decision",sa.String(40),nullable=False),
        sa.Column("rationale",sa.Text(),nullable=False),sa.Column("reason_codes",sa.JSON(),nullable=False),
        sa.Column("approved_amount",sa.Numeric(14,2)),sa.Column("denied_amount",sa.Numeric(14,2)),
        sa.Column("partial_line_decisions",sa.JSON(),nullable=False),sa.Column("evidence_snapshot",sa.JSON(),nullable=False),
        sa.Column("evidence_snapshot_sha256",sa.String(64),nullable=False),sa.Column("finding_refs",sa.JSON(),nullable=False),
        sa.Column("annotation_refs",sa.JSON(),nullable=False),sa.Column("inconsistency_refs",sa.JSON(),nullable=False),
        sa.Column("checkpoint_refs",sa.JSON(),nullable=False),sa.Column("ai_recommendation",sa.String(80)),
        sa.Column("ai_disagreement",sa.Boolean(),nullable=False),sa.Column("ai_disagreement_reason",sa.Text()),
        sa.Column("completeness",sa.JSON(),nullable=False),sa.Column("blocker_codes",sa.JSON(),nullable=False),
        sa.Column("escalation_queue",sa.String(100)),sa.Column("dual_control_required",sa.Boolean(),nullable=False),
        sa.Column("packet_version",sa.Integer(),nullable=False),sa.Column("expected_claim_status_version",sa.Integer(),nullable=False),
        sa.Column("locked_payload_sha256",sa.String(64)),sa.Column("decision_id",sa.String(128),sa.ForeignKey("human_review_decisions.decision_id",ondelete="RESTRICT")),
        sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("trace_id",sa.String(128)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("locked_at",sa.DateTime(timezone=True)),sa.Column("closed_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_review_decision_packet_idempotency"),
    )
    op.create_index("ix_review_decision_packet_claim","review_decision_packets",["tenant_id","claim_id","created_at"])
    op.create_index("ix_review_decision_packet_status","review_decision_packets",["tenant_id","status","updated_at"])

    op.create_table(
        "decision_second_reviews",
        sa.Column("second_review_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("packet_id",sa.String(128),sa.ForeignKey("review_decision_packets.packet_id",ondelete="CASCADE"),nullable=False),
        sa.Column("reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("action",sa.String(30),nullable=False),
        sa.Column("rationale",sa.Text(),nullable=False),sa.Column("packet_version",sa.Integer(),nullable=False),sa.Column("payload_sha256",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","packet_id","reviewer_user_id",name="uq_second_review_packet_reviewer"),
    )
    op.create_index("ix_second_review_packet","decision_second_reviews",["tenant_id","packet_id","created_at"])

    op.create_table(
        "adjudication_audit_events",
        sa.Column("audit_event_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("packet_id",sa.String(128),sa.ForeignKey("review_decision_packets.packet_id",ondelete="SET NULL")),
        sa.Column("sequence",sa.Integer(),nullable=False),sa.Column("event_type",sa.String(100),nullable=False),sa.Column("actor_type",sa.String(30),nullable=False),sa.Column("actor_id",sa.String(128),nullable=False),
        sa.Column("payload",sa.JSON(),nullable=False),sa.Column("previous_event_sha256",sa.String(64)),sa.Column("event_sha256",sa.String(64),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","claim_id","sequence",name="uq_adjudication_audit_sequence"),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_adjudication_audit_idempotency"),
    )
    op.create_index("ix_adjudication_audit_claim","adjudication_audit_events",["tenant_id","claim_id","sequence"])

    op.create_table(
        "decision_notification_intents",
        sa.Column("notification_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("packet_id",sa.String(128),sa.ForeignKey("review_decision_packets.packet_id",ondelete="CASCADE"),nullable=False),
        sa.Column("audience",sa.String(60),nullable=False),sa.Column("notification_type",sa.String(80),nullable=False),sa.Column("status",sa.String(40),nullable=False),
        sa.Column("payload_sha256",sa.String(64),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("delivered_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_decision_notification_idempotency"),
    )
    op.create_index("ix_decision_notification_claim","decision_notification_intents",["tenant_id","claim_id","created_at"])
    op.create_index("ix_decision_notification_status","decision_notification_intents",["tenant_id","status","created_at"])

    for table in ("review_decision_packets","decision_second_reviews","adjudication_audit_events","decision_notification_intents"):
        _tenant_rls(table)
    op.execute('CREATE TRIGGER decision_second_reviews_immutable BEFORE UPDATE OR DELETE ON "decision_second_reviews" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')
    op.execute('CREATE TRIGGER adjudication_audit_events_immutable BEFORE UPDATE OR DELETE ON "adjudication_audit_events" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    for table in ("decision_notification_intents","adjudication_audit_events","decision_second_reviews","review_decision_packets"):
        op.drop_table(table)
