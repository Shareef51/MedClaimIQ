from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.authentication import AuthenticationSessionModel
from app.repositories.authentication import AuthenticationSessionRepository
from app.security.oidc import AuthenticatedToken


class SessionSecurityError(ValueError):
    pass


class SessionFingerprint:
    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("session HMAC secret must be at least 32 characters")
        self._secret = secret.encode("utf-8")

    def digest(self, value: str) -> str:
        return hmac.new(self._secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


class AuthenticationSessionService:
    """Persists revocable application session state without storing bearer tokens."""

    def __init__(
        self,
        session: Session,
        *,
        hmac_secret: str,
        max_session_age_seconds: int = 43200,
        enforce_client_binding: bool = False,
    ) -> None:
        self.session = session
        self.fingerprint = SessionFingerprint(hmac_secret)
        if max_session_age_seconds < 300:
            raise ValueError("application session max age must be at least 300 seconds")
        self.max_session_age_seconds = max_session_age_seconds
        self.enforce_client_binding = enforce_client_binding

    def validate_or_create(
        self,
        *,
        token: AuthenticatedToken,
        user_id: str,
        tenant_id: str,
        client_fingerprint: str | None = None,
    ) -> AuthenticationSessionModel:
        external_session_value = token.session_id or token.jwt_id
        if external_session_value is None:
            raise SessionSecurityError("OIDC token must contain sid or jti for session enforcement")

        external_session_hash = self.fingerprint.digest(external_session_value)
        token_jti_hash = self.fingerprint.digest(token.jwt_id) if token.jwt_id else None
        client_hash = self.fingerprint.digest(client_fingerprint) if client_fingerprint else None
        repo = AuthenticationSessionRepository(self.session, tenant_id)
        auth_session = repo.get_by_external_session(
            issuer=token.issuer,
            subject=token.subject,
            external_session_hash=external_session_hash,
        )
        now = datetime.now(timezone.utc)
        if auth_session is not None:
            if auth_session.revoked_at is not None:
                raise SessionSecurityError("authentication session has been revoked")
            expires_at = auth_session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise SessionSecurityError("authentication session has expired")
            if (
                self.enforce_client_binding
                and client_hash
                and auth_session.client_fingerprint_hash not in {None, client_hash}
            ):
                raise SessionSecurityError("authentication session client binding mismatch")
            auth_session.last_seen_at = now
            auth_session.token_jti_hash = token_jti_hash
            if auth_session.client_fingerprint_hash is None:
                auth_session.client_fingerprint_hash = client_hash
            self.session.flush()
            return auth_session

        auth_session = AuthenticationSessionModel(
            session_id=f"as_{uuid4().hex}",
            tenant_id=tenant_id,
            user_id=user_id,
            issuer=token.issuer,
            subject=token.subject,
            external_session_hash=external_session_hash,
            token_jti_hash=token_jti_hash,
            client_fingerprint_hash=client_hash,
            authenticated_at=token.issued_at,
            last_seen_at=now,
            expires_at=now + timedelta(seconds=self.max_session_age_seconds),
        )
        return repo.add(auth_session)

    def revoke(
        self,
        *,
        tenant_id: str,
        session_id: str,
        revoked_by_user_id: str,
        reason: str,
    ) -> AuthenticationSessionModel:
        repo = AuthenticationSessionRepository(self.session, tenant_id)
        auth_session = repo.get(session_id)
        if auth_session is None:
            raise SessionSecurityError("authentication session does not exist in tenant")
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            auth_session.revoked_by_user_id = revoked_by_user_id
            auth_session.revocation_reason = reason[:500]
            self.session.flush()
        return auth_session
