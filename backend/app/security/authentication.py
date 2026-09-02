from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.access import Principal
from app.security.oidc import AuthenticatedToken, OIDCTokenVerifier, OIDCVerificationError
from app.security.session import AuthenticationSessionService, SessionSecurityError
from app.services.tenancy import PrincipalResolver


class AuthenticationError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class RequestIdentity:
    principal: Principal
    token: AuthenticatedToken
    application_session_id: str | None


class AuthenticationService:
    def __init__(
        self,
        *,
        token_verifier: OIDCTokenVerifier,
        session_hmac_secret: str,
        session_required: bool = True,
        session_max_age_seconds: int = 43200,
        enforce_client_binding: bool = False,
    ) -> None:
        self.token_verifier = token_verifier
        self.session_hmac_secret = session_hmac_secret
        self.session_required = session_required
        self.session_max_age_seconds = session_max_age_seconds
        self.enforce_client_binding = enforce_client_binding

    def authenticate(
        self,
        *,
        raw_token: str,
        tenant_id: str,
        db: Session,
        client_fingerprint: str | None = None,
    ) -> RequestIdentity:
        try:
            token = self.token_verifier.verify(raw_token)
        except OIDCVerificationError as exc:
            raise AuthenticationError(exc.code, str(exc), status_code=401) from exc

        principal = PrincipalResolver(db).resolve_external_identity(
            issuer=token.issuer,
            external_subject=token.subject,
            tenant_id=tenant_id,
        )
        if principal is None:
            raise AuthenticationError(
                "identity_not_mapped",
                "Authenticated identity has no active membership in the selected tenant",
                status_code=403,
            )
        if not principal.is_active:
            raise AuthenticationError(
                "inactive_identity",
                "Authenticated identity or tenant membership is inactive",
                status_code=403,
            )

        application_session_id: str | None = None
        if self.session_required:
            try:
                auth_session = AuthenticationSessionService(
                    db,
                    hmac_secret=self.session_hmac_secret,
                    max_session_age_seconds=self.session_max_age_seconds,
                    enforce_client_binding=self.enforce_client_binding,
                ).validate_or_create(
                    token=token,
                    user_id=principal.user_id,
                    tenant_id=tenant_id,
                    client_fingerprint=client_fingerprint,
                )
            except SessionSecurityError as exc:
                raise AuthenticationError("session_rejected", str(exc), status_code=401) from exc
            application_session_id = auth_session.session_id

        return RequestIdentity(
            principal=principal,
            token=token,
            application_session_id=application_session_id,
        )
