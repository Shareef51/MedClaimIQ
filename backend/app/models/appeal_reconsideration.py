from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AppealEvidenceSnapshotModel(Base):
    __tablename__ = "appeal_evidence_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "appeal_id", "snapshot_version", name="uq_appeal_evidence_snapshot_version"),
        UniqueConstraint("tenant_id", "snapshot_sha256", name="uq_appeal_evidence_snapshot_sha"),
        Index("ix_appeal_evidence_snapshot", "tenant_id", "appeal_id", "created_at"),
    )
    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    original_decision_id: Mapped[str] = mapped_column(ForeignKey("human_review_decisions.decision_id", ondelete="RESTRICT"), nullable=False)
    original_evidence_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    supplemental_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by_actor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppealEvidenceReingestionModel(Base):
    __tablename__ = "appeal_evidence_reingestions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "appeal_id", "source_kind", "source_id", "source_version", name="uq_appeal_reingestion_source_version"),
        Index("ix_appeal_reingestion", "tenant_id", "appeal_id", "status"),
    )
    reingestion_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    modality: Mapped[str] = mapped_column(String(30), nullable=False)
    media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_validation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    malware_verdict: Mapped[str] = mapped_column(String(40), nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(30), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_manifest: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_input_sha256s: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    retrieval_namespace: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppealEvidenceComparisonModel(Base):
    __tablename__ = "appeal_evidence_comparisons"
    __table_args__ = (Index("ix_appeal_evidence_comparison", "tenant_id", "appeal_id", "comparison_type"),)
    comparison_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("appeal_evidence_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    comparison_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field: Mapped[str] = mapped_column(String(120), nullable=False)
    original_source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    supplemental_source_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    original_value_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplemental_value_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealRAGRunModel(Base):
    __tablename__ = "appeal_rag_runs"
    __table_args__ = (Index("ix_appeal_rag_run", "tenant_id", "appeal_id", "created_at"),)
    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("appeal_evidence_snapshots.snapshot_id", ondelete="RESTRICT"), nullable=False)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    citation_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_fact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pack_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealRAGItemModel(Base):
    __tablename__ = "appeal_rag_items"
    __table_args__ = (Index("ix_appeal_rag_item", "tenant_id", "run_id", "rank"),)
    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("appeal_rag_runs.run_id", ondelete="CASCADE"), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    modality: Mapped[str] = mapped_column(String(30), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieval_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealReconsiderationRunModel(Base):
    __tablename__ = "appeal_reconsideration_runs"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_reconsideration_run_idempotency"), Index("ix_appeal_reconsideration_run", "tenant_id", "appeal_id", "created_at"),)
    reconsideration_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("appeal_evidence_snapshots.snapshot_id", ondelete="RESTRICT"), nullable=False)
    rag_run_id: Mapped[str] = mapped_column(ForeignKey("appeal_rag_runs.run_id", ondelete="RESTRICT"), nullable=False)
    graph_thread_id: Mapped[str] = mapped_column(String(160), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    changed_fact_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    contradiction_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_evidence_requests: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    escalation_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    adjudication_authority: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealReconsiderationCheckpointModel(Base):
    __tablename__ = "appeal_reconsideration_checkpoints"
    __table_args__ = (
        UniqueConstraint("tenant_id", "thread_id", "checkpoint_version", name="uq_appeal_checkpoint_version"),
        Index("ix_appeal_checkpoint", "tenant_id", "appeal_id", "status", "created_at"),
    )
    checkpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(160), nullable=False)
    checkpoint_version: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    state_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    state_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requires_human_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resumed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppealReviewerAnnotationModel(Base):
    __tablename__ = "appeal_reviewer_annotations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_annotation_idempotency"),
        Index("ix_appeal_annotation", "tenant_id", "appeal_id", "created_at"),
    )
    annotation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealMissingEvidenceRequestModel(Base):
    __tablename__ = "appeal_missing_evidence_requests"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_missing_evidence_idempotency"), Index("ix_appeal_missing_evidence", "tenant_id", "appeal_id", "status"),)
    request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    document_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealEscalationModel(Base):
    __tablename__ = "appeal_escalations"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_appeal_escalation_idempotency"), Index("ix_appeal_escalation", "tenant_id", "appeal_id", "status"),)
    escalation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeal_cases.appeal_id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    assigned_queue: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppealEvaluationCaseModel(Base):
    __tablename__ = "appeal_evaluation_cases"
    __table_args__ = (UniqueConstraint("tenant_id", "case_key", name="uq_appeal_eval_case_key"),)
    evaluation_case_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    case_key: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario: Mapped[str] = mapped_column(String(120), nullable=False)
    modalities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_changed_facts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_contradictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_recommendation_class: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_human_resolution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
