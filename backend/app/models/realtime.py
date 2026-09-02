from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class RealtimeOutboxModel(TimestampMixin, Base):
    __tablename__ = "realtime_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_realtime_outbox_event"),
        Index("ix_realtime_outbox_dispatch", "status", "available_at", "created_at"),
        Index("ix_realtime_outbox_tenant_claim", "tenant_id", "claim_id", "created_at"),
    )
    outbox_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(140), nullable=False)
    event_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    topic: Mapped[str] = mapped_column(String(180), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(180), nullable=False)
    envelope: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

class EventConsumerReceiptModel(Base):
    __tablename__ = "event_consumer_receipts"
    __table_args__ = (
        UniqueConstraint("consumer_group", "event_id", name="uq_consumer_event_once"),
        Index("ix_consumer_receipt_tenant_claim", "tenant_id", "claim_id", "processed_at"),
    )
    receipt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    consumer_group: Mapped[str] = mapped_column(String(160), nullable=False)
    topic: Mapped[str] = mapped_column(String(180), nullable=False)
    partition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class EventDeadLetterModel(Base):
    __tablename__ = "event_dead_letters"
    __table_args__ = (Index("ix_event_dlq_tenant_claim", "tenant_id", "claim_id", "created_at"),)
    dead_letter_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_topic: Mapped[str] = mapped_column(String(180), nullable=False)
    consumer_group: Mapped[str] = mapped_column(String(160), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    envelope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    replay_envelope: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_detail_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    replayed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class EventReplayRequestModel(Base):
    __tablename__ = "event_replay_requests"
    __table_args__ = (Index("ix_event_replay_tenant_status", "tenant_id", "status", "created_at"),)
    replay_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True)
    dead_letter_id: Mapped[str] = mapped_column(ForeignKey("event_dead_letters.dead_letter_id", ondelete="RESTRICT"), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    reason_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    target_topic: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class RealtimeStreamEventModel(Base):
    __tablename__ = "realtime_stream_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_realtime_stream_event"),
        Index("ix_realtime_stream_claim", "tenant_id", "claim_id", "stream_sequence"),
    )
    stream_sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(140), nullable=False)
    event_version: Mapped[str] = mapped_column(String(20), nullable=False)
    envelope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
