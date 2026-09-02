"""Production adjudication communications, appeals and post-decision operations.

Revision ID: 0031_post_decision_communications_appeals
Revises: 0030_governed_human_claim_closure
"""
from alembic import op
import sqlalchemy as sa

revision="0031_post_decision_communications_appeals"
down_revision="0030_governed_human_claim_closure"
branch_labels=None
depends_on=None


def _tenant_rls(table: str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")


def upgrade():
    op.create_table(
        "decision_notices",
        sa.Column("notice_id",sa.String(128),primary_key=True),
        sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("packet_id",sa.String(128),sa.ForeignKey("review_decision_packets.packet_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("decision_id",sa.String(128),sa.ForeignKey("human_review_decisions.decision_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("appeal_id",sa.String(128)),sa.Column("resolution_id",sa.String(128)),
        sa.Column("template_key",sa.String(100),nullable=False),sa.Column("template_version",sa.String(40),nullable=False),
        sa.Column("notice_version",sa.Integer(),nullable=False),sa.Column("audience",sa.String(60),nullable=False),sa.Column("status",sa.String(40),nullable=False),
        sa.Column("reason_explanations",sa.JSON(),nullable=False),sa.Column("rendered_payload",sa.JSON(),nullable=False),
        sa.Column("rendered_payload_sha256",sa.String(64),nullable=False),sa.Column("evidence_snapshot_sha256",sa.String(64),nullable=False),
        sa.Column("locked_decision_payload_sha256",sa.String(64),nullable=False),sa.Column("generated_by_actor_type",sa.String(30),nullable=False),
        sa.Column("generated_by_actor_id",sa.String(128),nullable=False),sa.Column("released_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),
        sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("released_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_decision_notice_idempotency"),
    )
    op.create_index("ix_decision_notice_claim","decision_notices",["tenant_id","claim_id","created_at"])
    op.create_index("ix_decision_notice_status","decision_notices",["tenant_id","status","updated_at"])

    op.create_table(
        "appeal_cases",
        sa.Column("appeal_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("original_packet_id",sa.String(128),sa.ForeignKey("review_decision_packets.packet_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("original_decision_id",sa.String(128),sa.ForeignKey("human_review_decisions.decision_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("notice_id",sa.String(128),sa.ForeignKey("decision_notices.notice_id",ondelete="RESTRICT"),nullable=False),sa.Column("status",sa.String(48),nullable=False),
        sa.Column("submitter_actor_type",sa.String(40),nullable=False),sa.Column("submitter_actor_id",sa.String(128),nullable=False),sa.Column("grounds",sa.JSON(),nullable=False),
        sa.Column("statement",sa.Text(),nullable=False),sa.Column("late_filing_reason",sa.Text()),sa.Column("appeal_due_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("submitted_at",sa.DateTime(timezone=True),nullable=False),sa.Column("assigned_reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),
        sa.Column("appeal_version",sa.Integer(),nullable=False),sa.Column("reopened_at",sa.DateTime(timezone=True)),sa.Column("resolved_at",sa.DateTime(timezone=True)),
        sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_case_idempotency"),
    )
    op.create_index("ix_appeal_claim","appeal_cases",["tenant_id","claim_id","created_at"])
    op.create_index("ix_appeal_status_due","appeal_cases",["tenant_id","status","appeal_due_at"])
    op.create_foreign_key("fk_decision_notice_appeal","decision_notices","appeal_cases",["appeal_id"],["appeal_id"],ondelete="SET NULL")

    op.create_table(
        "appeal_supplemental_evidence",
        sa.Column("link_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),
        sa.Column("evidence_id",sa.String(128),sa.ForeignKey("evidence_artifacts.evidence_id",ondelete="RESTRICT"),nullable=False),sa.Column("evidence_version",sa.Integer(),nullable=False),
        sa.Column("content_sha256",sa.String(64),nullable=False),sa.Column("linked_by_actor_type",sa.String(40),nullable=False),sa.Column("linked_by_actor_id",sa.String(128),nullable=False),
        sa.Column("linked_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","appeal_id","evidence_id",name="uq_appeal_supplemental_evidence"),
    )
    op.create_index("ix_appeal_supplemental","appeal_supplemental_evidence",["tenant_id","appeal_id","linked_at"])

    op.create_table(
        "appeal_review_assignments",
        sa.Column("assignment_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("assigned_by_actor_type",sa.String(40),nullable=False),
        sa.Column("assigned_by_actor_id",sa.String(128),nullable=False),sa.Column("independence_verified",sa.Boolean(),nullable=False),sa.Column("assignment_reason",sa.Text(),nullable=False),sa.Column("assigned_at",sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index("ix_appeal_assignment","appeal_review_assignments",["tenant_id","appeal_id","assigned_at"])

    op.create_table(
        "appeal_resolutions",
        sa.Column("resolution_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="RESTRICT"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),
        sa.Column("reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("outcome",sa.String(40),nullable=False),sa.Column("controlling_decision",sa.String(40),nullable=False),
        sa.Column("reason_codes",sa.JSON(),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("original_evidence_snapshot_sha256",sa.String(64),nullable=False),
        sa.Column("supplemental_evidence_snapshot",sa.JSON(),nullable=False),sa.Column("supplemental_evidence_sha256",sa.String(64),nullable=False),sa.Column("payload_sha256",sa.String(64),nullable=False),
        sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("resolved_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_resolution_idempotency"),sa.UniqueConstraint("tenant_id","appeal_id",name="uq_appeal_resolution_once"),
    )

    op.create_table(
        "decision_history_versions",
        sa.Column("history_version_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("sequence",sa.Integer(),nullable=False),
        sa.Column("source_type",sa.String(40),nullable=False),sa.Column("source_id",sa.String(128),nullable=False),sa.Column("decision",sa.String(40),nullable=False),
        sa.Column("human_reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("evidence_snapshot_sha256",sa.String(64),nullable=False),
        sa.Column("previous_version_sha256",sa.String(64)),sa.Column("version_payload_sha256",sa.String(64),nullable=False),sa.Column("version_sha256",sa.String(64),nullable=False),sa.Column("effective_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","claim_id","sequence",name="uq_decision_history_sequence"),sa.UniqueConstraint("tenant_id","source_type","source_id",name="uq_decision_history_source"),
    )
    op.create_index("ix_decision_history_claim","decision_history_versions",["tenant_id","claim_id","sequence"])

    op.create_table(
        "external_correspondence",
        sa.Column("correspondence_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="SET NULL")),
        sa.Column("notice_id",sa.String(128),sa.ForeignKey("decision_notices.notice_id",ondelete="SET NULL")),sa.Column("direction",sa.String(20),nullable=False),sa.Column("channel",sa.String(30),nullable=False),
        sa.Column("audience",sa.String(60),nullable=False),sa.Column("external_message_id",sa.String(160)),sa.Column("payload_sha256",sa.String(64),nullable=False),sa.Column("actor_type",sa.String(40),nullable=False),
        sa.Column("actor_id",sa.String(128),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_external_correspondence_idempotency"),
    )
    op.create_index("ix_correspondence_claim","external_correspondence",["tenant_id","claim_id","occurred_at"])

    op.create_table(
        "communication_delivery_attempts",
        sa.Column("attempt_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("notification_id",sa.String(128),sa.ForeignKey("decision_notification_intents.notification_id",ondelete="CASCADE"),nullable=False),
        sa.Column("attempt_number",sa.Integer(),nullable=False),sa.Column("channel",sa.String(30),nullable=False),sa.Column("success",sa.Boolean(),nullable=False),sa.Column("provider_message_id",sa.String(160)),
        sa.Column("error_code",sa.String(80)),sa.Column("error_detail_sha256",sa.String(64)),sa.Column("attempted_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","notification_id","attempt_number",name="uq_delivery_attempt_number"),
    )
    op.create_index("ix_delivery_attempt_notification","communication_delivery_attempts",["tenant_id","notification_id","attempt_number"])

    op.create_table(
        "communication_dead_letters",
        sa.Column("dead_letter_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("notification_id",sa.String(128),sa.ForeignKey("decision_notification_intents.notification_id",ondelete="CASCADE"),nullable=False),
        sa.Column("reason_code",sa.String(80),nullable=False),sa.Column("final_error_sha256",sa.String(64)),sa.Column("attempt_count",sa.Integer(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","notification_id",name="uq_communication_dlq_notification"),
    )

    op.create_table(
        "post_decision_tasks",
        sa.Column("task_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),
        sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE")),
        sa.Column("notice_id",sa.String(128),sa.ForeignKey("decision_notices.notice_id",ondelete="CASCADE")),sa.Column("task_type",sa.String(60),nullable=False),sa.Column("status",sa.String(30),nullable=False),
        sa.Column("priority",sa.Integer(),nullable=False),sa.Column("assigned_reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),sa.Column("due_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("breached_at",sa.DateTime(timezone=True)),sa.Column("completed_at",sa.DateTime(timezone=True)),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_post_decision_task_idempotency"),
    )
    op.create_index("ix_post_decision_task_queue","post_decision_tasks",["tenant_id","status","due_at","priority"])

    tables=("decision_notices","appeal_cases","appeal_supplemental_evidence","appeal_review_assignments","appeal_resolutions","decision_history_versions","external_correspondence","communication_delivery_attempts","communication_dead_letters","post_decision_tasks")
    for table in tables:_tenant_rls(table)
    immutable_triggers = {
        "appeal_supplemental_evidence": "appeal_supplemental_evidence_immutable",
        "appeal_review_assignments": "appeal_review_assignments_immutable",
        "appeal_resolutions": "appeal_resolutions_immutable",
        "decision_history_versions": "decision_history_versions_immutable",
        "external_correspondence": "external_correspondence_immutable",
        "communication_delivery_attempts": "communication_delivery_attempts_immutable",
        "communication_dead_letters": "communication_dead_letters_immutable",
    }
    for table, trigger in immutable_triggers.items():
        op.execute(f'CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    op.drop_constraint("fk_decision_notice_appeal","decision_notices",type_="foreignkey")
    for table in ("post_decision_tasks","communication_dead_letters","communication_delivery_attempts","external_correspondence","decision_history_versions","appeal_resolutions","appeal_review_assignments","appeal_supplemental_evidence","appeal_cases","decision_notices"):
        op.drop_table(table)
