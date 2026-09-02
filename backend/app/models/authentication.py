from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuthenticationSessionModel(TimestampMixin, Base):
    __tablename__ = "authentication_sessions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "issuer",
            "subject",
            "external_session_hash",
            name="external_session_per_tenant",
        ),
        Index("ix_auth_session_user_tenant", "tenant_id", "user_id"),
        Index("ix_auth_session_active_lookup", "tenant_id", "expires_at", "revoked_at"),
    )

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    external_session_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_jti_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_fingerprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.user_id", ondelete="SET NULL"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
