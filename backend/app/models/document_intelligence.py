from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DocumentExtractionRunModel(TimestampMixin, Base):
    __tablename__ = "document_extraction_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="idempotency_per_tenant"),
        UniqueConstraint("tenant_id", "evidence_id", "pipeline_version", "attempt_number", name="attempt_per_evidence_pipeline"),
        Index("ix_extraction_run_tenant_claim", "tenant_id", "claim_id", "status"),
        Index("ix_extraction_run_tenant_evidence", "tenant_id", "evidence_id", "created_at"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_event_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_processing_events.event_id", ondelete="SET NULL"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(80), nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregate_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 5), nullable=True)
    unit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parser_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(nullable=False, default=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    derived_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="SET NULL"), nullable=True)


class ExtractionUnitModel(Base):
    __tablename__ = "extraction_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "sequence", name="sequence_per_run"),
        Index("ix_extraction_unit_tenant_claim", "tenant_id", "claim_id", "unit_type"),
        Index("ix_extraction_unit_tenant_evidence", "tenant_id", "source_evidence_id", "sequence"),
    )

    unit_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("document_extraction_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    source_evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    unit_type: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    source_locator: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    citation_anchor: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExtractionDeadLetterModel(TimestampMixin, Base):
    __tablename__ = "extraction_dead_letters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", name="one_dead_letter_per_run"),
        Index("ix_extraction_dlq_tenant_claim", "tenant_id", "claim_id", "created_at"),
    )

    dead_letter_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("document_extraction_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_detail: Mapped[str] = mapped_column(Text, nullable=False)
    replay_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
