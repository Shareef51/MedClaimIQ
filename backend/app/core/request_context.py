from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_session_id: ContextVar[str | None] = ContextVar("current_session_id", default=None)


@dataclass(frozen=True)
class RequestContextTokens:
    tenant: Token[str | None]
    user: Token[str | None]
    session: Token[str | None]


def set_request_identity(*, tenant_id: str, user_id: str, session_id: str | None) -> RequestContextTokens:
    return RequestContextTokens(
        tenant=current_tenant_id.set(tenant_id),
        user=current_user_id.set(user_id),
        session=current_session_id.set(session_id),
    )


def reset_request_identity(tokens: RequestContextTokens) -> None:
    current_tenant_id.reset(tokens.tenant)
    current_user_id.reset(tokens.user)
    current_session_id.reset(tokens.session)
