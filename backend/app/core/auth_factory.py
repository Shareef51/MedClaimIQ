from __future__ import annotations

from app.core.config import Settings
from app.security.authentication import AuthenticationService
from app.security.oidc import OIDCTokenVerifier, RemoteJWKSProvider


def build_authentication_service(settings: Settings) -> AuthenticationService:
    jwks_provider = RemoteJWKSProvider(
        issuer=settings.oidc_issuer_url,
        timeout_seconds=settings.oidc_http_timeout_seconds,
        cache_ttl_seconds=settings.oidc_jwks_cache_ttl_seconds,
        allow_insecure_http=settings.oidc_allow_insecure_http,
    )
    verifier = OIDCTokenVerifier(
        issuer=settings.oidc_issuer_url,
        audience=settings.oidc_audience,
        jwks_provider=jwks_provider,
        allowed_algorithms=settings.oidc_algorithms,
        clock_skew_seconds=settings.oidc_clock_skew_seconds,
        required_scopes=settings.required_oidc_scopes,
    )
    return AuthenticationService(
        token_verifier=verifier,
        session_hmac_secret=settings.auth_session_hmac_secret.get_secret_value(),
        session_required=settings.auth_session_required,
        session_max_age_seconds=settings.auth_session_max_age_seconds,
        enforce_client_binding=settings.auth_enforce_client_binding,
    )
