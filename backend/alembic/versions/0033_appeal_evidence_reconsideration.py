"""Appeal evidence re-ingestion, recommendation-only agents and independent review workbench.

Revision ID: 0033_appeal_evidence_reconsideration
Revises: 0032_communication_delivery_compliance
"""
from alembic import op
import sqlalchemy as sa

revision="0033_appeal_evidence_reconsideration"
down_revision="0032_communication_delivery_compliance"
branch_labels=None
depends_on=None


def _tenant_rls(table:str):
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))")


def upgrade():
    op.create_table("appeal_evidence_snapshots",
        sa.Column("snapshot_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("snapshot_version",sa.Integer(),nullable=False),sa.Column("original_decision_id",sa.String(128),sa.ForeignKey("human_review_decisions.decision_id",ondelete="RESTRICT"),nullable=False),sa.Column("original_evidence_snapshot_sha256",sa.String(64),nullable=False),sa.Column("original_sources",sa.JSON(),nullable=False),sa.Column("supplemental_sources",sa.JSON(),nullable=False),sa.Column("modalities",sa.JSON(),nullable=False),sa.Column("source_count",sa.Integer(),nullable=False),sa.Column("snapshot_sha256",sa.String(64),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("created_by_actor_type",sa.String(30),nullable=False),sa.Column("created_by_actor_id",sa.String(128),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("locked_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("tenant_id","appeal_id","snapshot_version",name="uq_appeal_evidence_snapshot_version"),sa.UniqueConstraint("tenant_id","snapshot_sha256",name="uq_appeal_evidence_snapshot_sha"))
    op.create_index("ix_appeal_evidence_snapshot","appeal_evidence_snapshots",["tenant_id","appeal_id","created_at"])

    op.create_table("appeal_evidence_reingestions",
        sa.Column("reingestion_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("source_kind",sa.String(24),nullable=False),sa.Column("source_id",sa.String(256),nullable=False),sa.Column("source_version",sa.String(128),nullable=False),sa.Column("modality",sa.String(30),nullable=False),sa.Column("media_type",sa.String(160),nullable=False),sa.Column("content_sha256",sa.String(64),nullable=False),sa.Column("file_validation_status",sa.String(30),nullable=False),sa.Column("malware_verdict",sa.String(40),nullable=False),sa.Column("extraction_status",sa.String(30),nullable=False),sa.Column("chunk_count",sa.Integer(),nullable=False),sa.Column("chunk_manifest",sa.JSON(),nullable=False),sa.Column("embedding_model",sa.String(120),nullable=False),sa.Column("embedding_dimensions",sa.Integer(),nullable=False),sa.Column("embedding_input_sha256s",sa.JSON(),nullable=False),sa.Column("index_version",sa.String(80),nullable=False),sa.Column("retrieval_namespace",sa.String(180),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("error_code",sa.String(80)),sa.Column("error_detail",sa.Text()),sa.Column("trace_id",sa.String(128)),sa.Column("started_at",sa.DateTime(timezone=True),nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("tenant_id","appeal_id","source_kind","source_id","source_version",name="uq_appeal_reingestion_source_version"))
    op.create_index("ix_appeal_reingestion","appeal_evidence_reingestions",["tenant_id","appeal_id","status"])

    op.create_table("appeal_evidence_comparisons",
        sa.Column("comparison_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("snapshot_id",sa.String(128),sa.ForeignKey("appeal_evidence_snapshots.snapshot_id",ondelete="CASCADE"),nullable=False),sa.Column("comparison_type",sa.String(30),nullable=False),sa.Column("field",sa.String(120),nullable=False),sa.Column("original_source_ref",sa.String(256)),sa.Column("supplemental_source_ref",sa.String(256),nullable=False),sa.Column("original_value_sha256",sa.String(64)),sa.Column("supplemental_value_sha256",sa.String(64),nullable=False),sa.Column("severity",sa.String(30),nullable=False),sa.Column("confidence",sa.Float(),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("citations",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_appeal_evidence_comparison","appeal_evidence_comparisons",["tenant_id","appeal_id","comparison_type"])

    op.create_table("appeal_rag_runs",
        sa.Column("run_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("snapshot_id",sa.String(128),sa.ForeignKey("appeal_evidence_snapshots.snapshot_id",ondelete="RESTRICT"),nullable=False),sa.Column("query_sha256",sa.String(64),nullable=False),sa.Column("strategy",sa.String(80),nullable=False),sa.Column("candidate_count",sa.Integer(),nullable=False),sa.Column("selected_count",sa.Integer(),nullable=False),sa.Column("citation_coverage",sa.Float(),nullable=False),sa.Column("contradiction_count",sa.Integer(),nullable=False),sa.Column("changed_fact_count",sa.Integer(),nullable=False),sa.Column("pack_sha256",sa.String(64),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_appeal_rag_run","appeal_rag_runs",["tenant_id","appeal_id","created_at"])

    op.create_table("appeal_rag_items",
        sa.Column("item_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("run_id",sa.String(128),sa.ForeignKey("appeal_rag_runs.run_id",ondelete="CASCADE"),nullable=False),sa.Column("source_scope",sa.String(24),nullable=False),sa.Column("source_id",sa.String(256),nullable=False),sa.Column("source_version",sa.String(128),nullable=False),sa.Column("modality",sa.String(30),nullable=False),sa.Column("rank",sa.Integer(),nullable=False),sa.Column("score",sa.Float(),nullable=False),sa.Column("content_sha256",sa.String(64),nullable=False),sa.Column("text_preview",sa.Text(),nullable=False),sa.Column("citation",sa.JSON(),nullable=False),sa.Column("retrieval_sources",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_appeal_rag_item","appeal_rag_items",["tenant_id","run_id","rank"])

    op.create_table("appeal_reconsideration_runs",
        sa.Column("reconsideration_run_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("snapshot_id",sa.String(128),sa.ForeignKey("appeal_evidence_snapshots.snapshot_id",ondelete="RESTRICT"),nullable=False),sa.Column("rag_run_id",sa.String(128),sa.ForeignKey("appeal_rag_runs.run_id",ondelete="RESTRICT"),nullable=False),sa.Column("graph_thread_id",sa.String(160),nullable=False),sa.Column("agent_name",sa.String(80),nullable=False),sa.Column("prompt_version",sa.String(80),nullable=False),sa.Column("recommendation",sa.String(40),nullable=False),sa.Column("confidence",sa.Float(),nullable=False),sa.Column("recommendation_summary",sa.Text(),nullable=False),sa.Column("recommendation_sha256",sa.String(64),nullable=False),sa.Column("evidence_refs",sa.JSON(),nullable=False),sa.Column("changed_fact_refs",sa.JSON(),nullable=False),sa.Column("contradiction_refs",sa.JSON(),nullable=False),sa.Column("missing_evidence_requests",sa.JSON(),nullable=False),sa.Column("escalation_reasons",sa.JSON(),nullable=False),sa.Column("requires_human_review",sa.Boolean(),nullable=False),sa.Column("adjudication_authority",sa.String(20),nullable=False),sa.Column("trace_id",sa.String(128)),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_reconsideration_run_idempotency"))
    op.create_index("ix_appeal_reconsideration_run","appeal_reconsideration_runs",["tenant_id","appeal_id","created_at"])

    op.create_table("appeal_reconsideration_checkpoints",
        sa.Column("checkpoint_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("thread_id",sa.String(160),nullable=False),sa.Column("checkpoint_version",sa.Integer(),nullable=False),sa.Column("stage",sa.String(80),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("state_metadata",sa.JSON(),nullable=False),sa.Column("state_sha256",sa.String(64),nullable=False),sa.Column("requires_human_action",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("resumed_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT")),sa.Column("resumed_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("tenant_id","thread_id","checkpoint_version",name="uq_appeal_checkpoint_version"))
    op.create_index("ix_appeal_checkpoint","appeal_reconsideration_checkpoints",["tenant_id","appeal_id","status","created_at"])

    op.create_table("appeal_reviewer_annotations",
        sa.Column("annotation_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("reviewer_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("target_type",sa.String(40),nullable=False),sa.Column("target_id",sa.String(180),nullable=False),sa.Column("body",sa.Text(),nullable=False),sa.Column("body_sha256",sa.String(64),nullable=False),sa.Column("anchor",sa.JSON(),nullable=False),sa.Column("tags",sa.JSON(),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_annotation_idempotency"))
    op.create_index("ix_appeal_annotation","appeal_reviewer_annotations",["tenant_id","appeal_id","created_at"])

    op.create_table("appeal_missing_evidence_requests",
        sa.Column("request_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("requested_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("document_types",sa.JSON(),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_missing_evidence_idempotency"))
    op.create_index("ix_appeal_missing_evidence","appeal_missing_evidence_requests",["tenant_id","appeal_id","status"])

    op.create_table("appeal_escalations",
        sa.Column("escalation_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("claim_id",sa.String(128),sa.ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False),sa.Column("appeal_id",sa.String(128),sa.ForeignKey("appeal_cases.appeal_id",ondelete="CASCADE"),nullable=False),sa.Column("level",sa.String(30),nullable=False),sa.Column("reason",sa.Text(),nullable=False),sa.Column("created_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("assigned_queue",sa.String(80),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("idempotency_key",sa.String(180),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","idempotency_key",name="uq_appeal_escalation_idempotency"))
    op.create_index("ix_appeal_escalation","appeal_escalations",["tenant_id","appeal_id","status"])

    op.create_table("appeal_evaluation_cases",
        sa.Column("evaluation_case_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(64),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False),sa.Column("case_key",sa.String(160),nullable=False),sa.Column("scenario",sa.String(120),nullable=False),sa.Column("modalities",sa.JSON(),nullable=False),sa.Column("expected_changed_facts",sa.JSON(),nullable=False),sa.Column("expected_contradictions",sa.JSON(),nullable=False),sa.Column("expected_recommendation_class",sa.String(40),nullable=False),sa.Column("requires_human_resolution",sa.Boolean(),nullable=False),sa.Column("dataset_version",sa.String(40),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","case_key",name="uq_appeal_eval_case_key"))

    tables=("appeal_evidence_snapshots","appeal_evidence_reingestions","appeal_evidence_comparisons","appeal_rag_runs","appeal_rag_items","appeal_reconsideration_runs","appeal_reconsideration_checkpoints","appeal_reviewer_annotations","appeal_missing_evidence_requests","appeal_escalations","appeal_evaluation_cases")
    for table in tables:_tenant_rls(table)

    # Locked snapshot payload fields cannot be rewritten; only lifecycle status can move to superseded.
    op.execute("""
    CREATE OR REPLACE FUNCTION medclaimiq_appeal_snapshot_payload_immutable() RETURNS trigger AS $$
    BEGIN
      IF OLD.snapshot_sha256 <> NEW.snapshot_sha256 OR OLD.original_sources <> NEW.original_sources OR OLD.supplemental_sources <> NEW.supplemental_sources OR OLD.original_evidence_snapshot_sha256 <> NEW.original_evidence_snapshot_sha256 THEN
        RAISE EXCEPTION 'locked appeal evidence snapshot payload is immutable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute('CREATE TRIGGER appeal_evidence_snapshot_payload_immutable BEFORE UPDATE ON "appeal_evidence_snapshots" FOR EACH ROW EXECUTE FUNCTION medclaimiq_appeal_snapshot_payload_immutable()')
    for table,trigger in {
        "appeal_evidence_comparisons":"appeal_evidence_comparisons_immutable",
        "appeal_rag_runs":"appeal_rag_runs_immutable",
        "appeal_rag_items":"appeal_rag_items_immutable",
        "appeal_reconsideration_runs":"appeal_reconsideration_runs_immutable",
        "appeal_reviewer_annotations":"appeal_reviewer_annotations_immutable",
    }.items():
        op.execute(f'CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION medclaimiq_reject_immutable_change()')


def downgrade():
    for table in ("appeal_evaluation_cases","appeal_escalations","appeal_missing_evidence_requests","appeal_reviewer_annotations","appeal_reconsideration_checkpoints","appeal_reconsideration_runs","appeal_rag_items","appeal_rag_runs","appeal_evidence_comparisons","appeal_evidence_reingestions","appeal_evidence_snapshots"):
        op.drop_table(table)
