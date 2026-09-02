"""External patient/provider portal persistence and immutable audit.

Revision ID: 0018_patient_provider_portal
Revises: 0017_human_review_workbench
"""
from alembic import op
import sqlalchemy as sa
revision="0018_patient_provider_portal"; down_revision="0017_human_review_workbench"; branch_labels=None; depends_on=None
TABLES=("portal_document_requests","portal_submissions","portal_action_events")

def _rls(table:str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'CREATE POLICY {table}_tenant_isolation ON "{table}" USING (tenant_id = current_setting(\'app.current_tenant_id\', true)) WITH CHECK (tenant_id = current_setting(\'app.current_tenant_id\', true))')

def upgrade():
    op.create_table("portal_document_requests",
        sa.Column("request_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("source_decision_id",sa.String(128),sa.ForeignKey("human_review_decisions.decision_id",ondelete="SET NULL")),sa.Column("requested_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("requested_document_types",sa.JSON(),nullable=False),sa.Column("instructions",sa.Text(),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("responded_at",sa.DateTime(timezone=True)),sa.Column("satisfied_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","source_decision_id",name="uq_portal_request_source_decision"))
    op.create_index("ix_portal_request_claim","portal_document_requests",["tenant_id","claim_id","status","created_at"])
    op.create_table("portal_submissions",
        sa.Column("submission_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("request_id",sa.String(128),sa.ForeignKey("portal_document_requests.request_id",ondelete="CASCADE"),nullable=False),
        sa.Column("submitted_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("upload_session_id",sa.String(128),sa.ForeignKey("evidence_upload_sessions.upload_session_id",ondelete="RESTRICT"),nullable=False),sa.Column("evidence_id",sa.String(128),sa.ForeignKey("evidence_artifacts.evidence_id",ondelete="SET NULL")),sa.Column("document_type",sa.String(80),nullable=False),sa.Column("status",sa.String(40),nullable=False),sa.Column("acknowledgement_code",sa.String(80),nullable=False,unique=True),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("received_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","upload_session_id",name="uq_portal_submission_upload"),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_portal_submission_idempotency"))
    op.create_index("ix_portal_submission_claim","portal_submissions",["tenant_id","claim_id","created_at"])
    op.create_table("portal_action_events",
        sa.Column("event_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("actor_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("event_type",sa.String(100),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_portal_action_idempotency"))
    op.create_index("ix_portal_action_claim","portal_action_events",["tenant_id","claim_id","occurred_at"])
    for t in TABLES:_rls(t)
    op.execute('CREATE TRIGGER portal_action_events_immutable BEFORE UPDATE OR DELETE ON "portal_action_events" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')

def downgrade():
    for t in reversed(TABLES):op.drop_table(t)
