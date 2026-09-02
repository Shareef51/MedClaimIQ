from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentWorkflowModel(Base):
    __tablename__ = "agent_workflows"
    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "workflow_key", name="uq_agent_workflow_claim_key"),
        Index("ix_agent_workflow_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_agent_workflow_status", "tenant_id", "status", "updated_at"),
    )
    workflow_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_pack_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    guardrail_run_id: Mapped[str | None] = mapped_column(ForeignKey("rag_guardrail_runs.run_id", ondelete="SET NULL"), nullable=True)
    workflow_key: Mapped[str] = mapped_column(String(160), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    selected_agents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    completed_agents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failed_agents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentExecutionModel(Base):
    __tablename__ = "agent_executions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "workflow_id", "agent_name", "attempt", name="uq_agent_execution_attempt"),
        Index("ix_agent_execution_workflow", "tenant_id", "workflow_id", "created_at"),
        CheckConstraint("attempt >= 1", name="agent_execution_attempt_positive"),
    )
    execution_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentFindingModel(Base):
    __tablename__ = "agent_findings"
    __table_args__ = (
        Index("ix_agent_finding_workflow", "tenant_id", "workflow_id", "agent_name"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="agent_finding_confidence_range"),
    )
    finding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.execution_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    summary_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finding_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentHumanCheckpointModel(Base):
    __tablename__ = "agent_human_checkpoints"
    __table_args__ = (
        Index("ix_agent_checkpoint_workflow", "tenant_id", "workflow_id", "created_at"),
        Index("ix_agent_checkpoint_status", "tenant_id", "status", "created_at"),
    )
    checkpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    message_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    required_permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    checkpoint_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="waiting")
    resumed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=True)
    resume_action: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resume_comment_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentWorkflowEventModel(Base):
    __tablename__ = "agent_workflow_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_agent_workflow_event_idempotency"),
        Index("ix_agent_workflow_event", "tenant_id", "workflow_id", "sequence"),
        CheckConstraint("sequence >= 1", name="agent_workflow_event_sequence_positive"),
    )
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentModelInvocationModel(Base):
    __tablename__ = "agent_model_invocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "workflow_id", "agent_name", "attempt", name="uq_agent_model_invocation_attempt"),
        Index("ix_agent_model_invocation_workflow", "tenant_id", "workflow_id", "created_at"),
    )
    invocation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="RESTRICT"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_key: Mapped[str] = mapped_column(String(160), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_context_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    output_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_response_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentToolAuditModel(Base):
    __tablename__ = "agent_tool_audits"
    __table_args__ = (
        Index("ix_agent_tool_audit_workflow", "tenant_id", "workflow_id", "agent_name", "created_at"),
    )
    audit_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("agent_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    invocation_id: Mapped[str] = mapped_column(ForeignKey("agent_model_invocations.invocation_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
