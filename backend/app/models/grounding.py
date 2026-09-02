from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RAGGuardrailRunModel(Base):
    __tablename__ = "rag_guardrail_runs"
    __table_args__ = (
        Index("ix_rag_guardrail_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_rag_guardrail_pack", "tenant_id", "pack_id"),
        CheckConstraint("evidence_quality >= 0 AND evidence_quality <= 1", name="guardrail_quality_range"),
        CheckConstraint("answerability_score >= 0 AND answerability_score <= 1", name="guardrail_answerability_range"),
    )
    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_length: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    guardrail_version: Mapped[str] = mapped_column(String(120), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    answerable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answerability_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_quality: Mapped[float] = mapped_column(Float, nullable=False)
    safe_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_injection_count: Mapped[int] = mapped_column(Integer, nullable=False)
    supported_statement_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_statement_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unresolved_material_contradictions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repair_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalation_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RAGPromptInjectionFindingModel(Base):
    __tablename__ = "rag_prompt_injection_findings"
    __table_args__ = (
        Index("ix_rag_injection_run", "tenant_id", "run_id", "risk"),
        CheckConstraint("score >= 0 AND score <= 1", name="rag_injection_score_range"),
    )
    finding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_key: Mapped[str] = mapped_column(String(128), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    risk: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RAGStatementGroundingModel(Base):
    __tablename__ = "rag_statement_grounding_checks"
    __table_args__ = (
        Index("ix_rag_statement_run", "tenant_id", "run_id", "support_status"),
        CheckConstraint("support_score >= 0 AND support_score <= 1", name="rag_statement_score_range"),
    )
    check_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    statement_id: Mapped[str] = mapped_column(String(128), nullable=False)
    statement_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    support_status: Mapped[str] = mapped_column(String(30), nullable=False)
    support_score: Mapped[float] = mapped_column(Float, nullable=False)
    citation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    cited_evidence_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    invalid_evidence_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    numeric_integrity: Mapped[bool] = mapped_column(Boolean, nullable=False)
    medical_code_integrity: Mapped[bool] = mapped_column(Boolean, nullable=False)
    contradiction_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RAGRepairAttemptModel(Base):
    __tablename__ = "rag_guardrail_repair_attempts"
    __table_args__ = (
        Index("ix_rag_repair_run", "tenant_id", "run_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1 AND attempt_number <= 5", name="rag_repair_attempt_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="rag_repair_confidence_range"),
    )
    repair_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_retrievers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    result_pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    answerable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RAGHumanReviewEscalationModel(Base):
    __tablename__ = "rag_human_review_escalations"
    __table_args__ = (
        Index("ix_rag_human_escalation_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_rag_human_escalation_run", "tenant_id", "run_id"),
    )
    escalation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rag_guardrail_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("rag_evidence_packs.pack_id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
