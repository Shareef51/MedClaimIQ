from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MultimodalReviewAnnotationModel(Base):
    __tablename__ = "multimodal_review_annotations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_multimodal_review_annotation_idempotency"),
        Index("ix_multimodal_review_annotation_claim", "tenant_id", "claim_id", "created_at"),
        Index("ix_multimodal_review_annotation_target", "tenant_id", "claim_id", "target_type", "target_id"),
    )

    annotation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("user_accounts.user_id", ondelete="RESTRICT"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(180), nullable=False)
    annotation_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    anchor: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
