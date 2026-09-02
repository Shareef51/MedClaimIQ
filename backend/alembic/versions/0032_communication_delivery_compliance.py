"""Production post-decision communication delivery, compliance and reconciliation.

Revision ID: 0032_communication_delivery_compliance
Revises: 0031_post_decision_communications_appeals
"""
from alembic import op
import sqlalchemy as sa

revision="0032_communication_delivery_compliance"
down_revision="0031_post_decision_communications_appeals"
branch_labels=None
depends_on=None


def _tenant_rls(table:str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")


def upgrade():
    op.create_table("communication_endpoints",
        sa.Column("endpoint_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("audience",sa.String(60),nullable=False),sa.Column("channel",sa.String(20),nullable=False),sa.Column("destination_ciphertext",sa.Text(),nullable=False),sa.Column("destination_fingerprint",sa.String(64),nullable=False),sa.Column("encryption_key_version",sa.String(40),nullable=False),sa.Column("consent_status",sa.String(30),nullable=False),sa.Column("locale",sa.String(12),nullable=False),sa.Column("accessibility_preferences",sa.JSON(),nullable=False),sa.Column("endpoint_version",sa.Integer(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("updated_by_actor_type",sa.String(40),nullable=False),sa.Column("updated_by_actor_id",sa.String(128),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","claim_id","audience","channel",name="uq_comm_endpoint_claim_audience_channel"))
    op.create_index("ix_comm_endpoint_claim","communication_endpoints",["tenant_id","claim_id","audience"])

    op.create_table("communication_templates",
        sa.Column("template_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("template_key",sa.String(100),nullable=False),sa.Column("template_version",sa.String(40),nullable=False),sa.Column("locale",sa.String(12),nullable=False),sa.Column("channel",sa.String(20),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("subject_template",sa.Text()),sa.Column("body_template",sa.Text(),nullable=False),sa.Column("accessibility_schema",sa.JSON(),nullable=False),sa.Column("content_sha256",sa.String(64),nullable=False),sa.Column("change_reason",sa.Text(),nullable=False),sa.Column("created_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("approved_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("approved_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id","template_key","template_version","locale","channel",name="uq_comm_template_version"))
    op.create_index("ix_comm_template_lookup","communication_templates",["tenant_id","template_key","locale","channel","status"])

    op.create_table("communication_dispatches",
        sa.Column("dispatch_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("notice_id",sa.String(128),sa.ForeignKey("decision_notices.notice_id",ondelete="CASCADE"),nullable=False),sa.Column("notification_id",sa.String(128),sa.ForeignKey("decision_notification_intents.notification_id",ondelete="CASCADE"),nullable=False),sa.Column("endpoint_id",sa.String(128),sa.ForeignKey("communication_endpoints.endpoint_id",ondelete="RESTRICT"),nullable=False),sa.Column("template_id",sa.String(128),sa.ForeignKey("communication_templates.template_id",ondelete="RESTRICT"),nullable=False),sa.Column("channel",sa.String(20),nullable=False),sa.Column("provider_name",sa.String(60),nullable=False),sa.Column("locale",sa.String(12),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("rendered_payload",sa.JSON(),nullable=False),sa.Column("rendered_payload_sha256",sa.String(64),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("attempt_count",sa.Integer(),nullable=False),sa.Column("next_attempt_at",sa.DateTime(timezone=True),nullable=False),sa.Column("regulatory_deadline_at",sa.DateTime(timezone=True),nullable=False),sa.Column("lease_owner",sa.String(128)),sa.Column("lease_until",sa.DateTime(timezone=True)),sa.Column("provider_message_id",sa.String(180)),sa.Column("last_error_code",sa.String(80)),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("sent_at",sa.DateTime(timezone=True)),sa.Column("delivered_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_comm_dispatch_idempotency"))
    op.create_index("ix_comm_dispatch_worker","communication_dispatches",["tenant_id","status","next_attempt_at","lease_until"])
    op.create_index("ix_comm_dispatch_claim","communication_dispatches",["tenant_id","claim_id","created_at"])

    op.create_table("communication_receipts",
        sa.Column("receipt_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("dispatch_id",sa.String(128),sa.ForeignKey("communication_dispatches.dispatch_id",ondelete="CASCADE"),nullable=False),sa.Column("provider_name",sa.String(60),nullable=False),sa.Column("provider_event_id",sa.String(180),nullable=False),sa.Column("provider_message_id",sa.String(180)),sa.Column("status",sa.String(30),nullable=False),sa.Column("payload_sha256",sa.String(64),nullable=False),sa.Column("signature_verified",sa.Boolean(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("received_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","provider_name","provider_event_id",name="uq_comm_receipt_provider_event"))
    op.create_index("ix_comm_receipt_dispatch","communication_receipts",["tenant_id","dispatch_id","occurred_at"])

    op.create_table("communication_reconciliations",
        sa.Column("reconciliation_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("notice_id",sa.String(128),sa.ForeignKey("decision_notices.notice_id",ondelete="CASCADE"),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("expected_dispatches",sa.Integer(),nullable=False),sa.Column("delivered_dispatches",sa.Integer(),nullable=False),sa.Column("failed_dispatches",sa.Integer(),nullable=False),sa.Column("gaps",sa.JSON(),nullable=False),sa.Column("reconciliation_sha256",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_comm_recon_claim","communication_reconciliations",["tenant_id","claim_id","created_at"])

    op.create_table("communication_legal_holds",
        sa.Column("hold_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("reason",sa.Text(),nullable=False),sa.Column("placed_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("placed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("released_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),sa.Column("released_at",sa.DateTime(timezone=True)),sa.Column("release_reason",sa.Text()))
    op.create_index("ix_comm_hold_claim","communication_legal_holds",["tenant_id","claim_id","released_at"])

    op.create_table("communication_incidents",
        sa.Column("incident_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="SET NULL")),sa.Column("dispatch_id",sa.String(128),sa.ForeignKey("communication_dispatches.dispatch_id",ondelete="SET NULL")),sa.Column("severity",sa.String(20),nullable=False),sa.Column("category",sa.String(60),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("summary",sa.Text(),nullable=False),sa.Column("recovery_action",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("recovered_at",sa.DateTime(timezone=True)))
    op.create_index("ix_comm_incident_status","communication_incidents",["tenant_id","status","created_at"])

    tables=("communication_endpoints","communication_templates","communication_dispatches","communication_receipts","communication_reconciliations","communication_legal_holds","communication_incidents")
    for table in tables:_tenant_rls(table)

    for table,trigger in {"communication_receipts":"communication_receipts_immutable","communication_reconciliations":"communication_reconciliations_immutable"}.items():
        op.execute(f'CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')

    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_reject_approved_template_change() RETURNS trigger AS $$
    BEGIN
      IF OLD.status = 'approved' THEN RAISE EXCEPTION 'approved communication template versions are immutable'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute('CREATE TRIGGER communication_templates_approved_immutable BEFORE UPDATE OR DELETE ON "communication_templates" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_approved_template_change()')


def downgrade():
    for table in ("communication_incidents","communication_legal_holds","communication_reconciliations","communication_receipts","communication_dispatches","communication_templates","communication_endpoints"):
        op.drop_table(table)
