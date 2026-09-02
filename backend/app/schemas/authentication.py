from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthenticationContextResponse(BaseModel):
    user_id: str
    tenant_id: str
    role: str
    application_session_id: str | None
    token_issuer: str
    token_subject: str
    token_expires_at: datetime
    scopes: list[str]


class SessionRevokeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SessionRevokeResponse(BaseModel):
    session_id: str
    revoked: bool
    revoked_at: datetime | None
