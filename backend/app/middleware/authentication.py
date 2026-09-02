from __future__ import annotations

import hashlib
from collections.abc import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.request_context import reset_request_identity, set_request_identity
from app.db.session import get_session_factory
from app.security.authentication import AuthenticationError, AuthenticationService


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authenticates protected API requests and binds verified tenant context."""

    def __init__(
        self,
        app,
        *,
        public_paths: Iterable[str],
        tenant_header: str = "X-Tenant-Id",
    ) -> None:
        super().__init__(app)
        self.public_paths = frozenset(public_paths)
        self.tenant_header = tenant_header

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if request.method == "OPTIONS" or self._is_public(path):
            return await call_next(request)
        if not path.startswith("/api/") and path != "/mcp":
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return self._error(401, "missing_bearer_token", "Bearer authentication is required")
        raw_token = authorization[7:].strip()
        tenant_id = request.headers.get(self.tenant_header, "").strip()
        if not tenant_id:
            return self._error(400, "missing_tenant_context", f"{self.tenant_header} is required")

        auth_service: AuthenticationService = request.app.state.authentication_service
        session_factory_provider = getattr(request.app.state, "session_factory_provider", get_session_factory)
        db = session_factory_provider()()
        context_tokens = None
        try:
            identity = auth_service.authenticate(
                raw_token=raw_token,
                tenant_id=tenant_id,
                db=db,
                client_fingerprint=self._client_fingerprint(request),
            )
            db.commit()
            request.state.identity = identity
            request.state.principal = identity.principal
            request.state.tenant_id = identity.principal.tenant_id
            request.state.user_id = identity.principal.user_id
            request.state.auth_session_id = identity.application_session_id
            context_tokens = set_request_identity(
                tenant_id=identity.principal.tenant_id,
                user_id=identity.principal.user_id,
                session_id=identity.application_session_id,
            )
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        except AuthenticationError as exc:
            db.rollback()
            return self._error(exc.status_code, exc.code, str(exc))
        finally:
            if context_tokens is not None:
                reset_request_identity(context_tokens)
            db.close()

    def _is_public(self, path: str) -> bool:
        exact = path in self.public_paths
        wildcard = any(item.endswith("*") and path.startswith(item[:-1]) for item in self.public_paths)
        return exact or wildcard or path.startswith("/docs") or path.startswith("/redoc")

    @staticmethod
    def _client_fingerprint(request: Request) -> str | None:
        user_agent = request.headers.get("User-Agent", "")[:512]
        # Never persist the raw client IP. The prefix merely adds a weak session-binding
        # signal and is hashed again with the server HMAC secret before persistence.
        client_host = request.client.host if request.client else ""
        if not user_agent and not client_host:
            return None
        network_hint = ":".join(client_host.split(":")[:4]) if ":" in client_host else ".".join(client_host.split(".")[:3])
        return hashlib.sha256(f"{user_agent}|{network_hint}".encode("utf-8")).hexdigest()

    @staticmethod
    def _error(status_code: int, code: str, message: str) -> JSONResponse:
        headers = {"Cache-Control": "no-store"}
        if status_code == 401:
            headers["WWW-Authenticate"] = "Bearer"
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": code, "message": message}},
            headers=headers,
        )
