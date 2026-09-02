from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
import jwt
from jwt import InvalidTokenError, PyJWK


class OIDCVerificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AuthenticatedToken:
    issuer: str
    subject: str
    audience: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    not_before: datetime | None
    jwt_id: str | None
    session_id: str | None
    scopes: frozenset[str]
    claims: dict[str, Any]


class JWKSProvider(Protocol):
    def get_jwk(self, kid: str) -> dict[str, Any]: ...


class RemoteJWKSProvider:
    """OIDC discovery + JWKS client with bounded in-memory caching.

    Discovery and JWKS responses are treated as identity-provider configuration,
    never as application authorization state. Tenant/role membership is resolved
    from MedClaimIQ persistence after token verification.
    """

    def __init__(
        self,
        *,
        issuer: str,
        timeout_seconds: float = 5.0,
        cache_ttl_seconds: int = 300,
        allow_insecure_http: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.allow_insecure_http = allow_insecure_http
        self._client = client
        self._lock = RLock()
        self._jwks_uri: str | None = None
        self._keys: dict[str, dict[str, Any]] = {}
        self._expires_at = 0.0

    def _http_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme == "https":
            return
        if self.allow_insecure_http and parsed.scheme == "http" and parsed.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            return
        raise OIDCVerificationError("oidc_insecure_url", "OIDC endpoints must use HTTPS")

    def _discover_jwks_uri(self) -> str:
        discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        self._validate_url(discovery_url)
        try:
            response = self._http_client().get(discovery_url)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OIDCVerificationError("oidc_discovery_failed", "OIDC discovery failed") from exc

        if payload.get("issuer") != self.issuer:
            raise OIDCVerificationError("oidc_issuer_mismatch", "OIDC discovery issuer mismatch")
        jwks_uri = payload.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise OIDCVerificationError("oidc_missing_jwks_uri", "OIDC discovery has no JWKS URI")
        self._validate_url(jwks_uri)
        self._jwks_uri = jwks_uri
        return jwks_uri

    def _refresh(self) -> None:
        jwks_uri = self._jwks_uri or self._discover_jwks_uri()
        try:
            response = self._http_client().get(jwks_uri)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OIDCVerificationError("oidc_jwks_failed", "OIDC JWKS retrieval failed") from exc

        keys = payload.get("keys")
        if not isinstance(keys, list):
            raise OIDCVerificationError("oidc_invalid_jwks", "OIDC JWKS response is invalid")

        mapped: dict[str, dict[str, Any]] = {}
        for key in keys:
            if isinstance(key, dict) and isinstance(key.get("kid"), str):
                mapped[key["kid"]] = key
        if not mapped:
            raise OIDCVerificationError("oidc_empty_jwks", "OIDC JWKS contains no keyed signing keys")
        self._keys = mapped
        self._expires_at = monotonic() + self.cache_ttl_seconds

    def get_jwk(self, kid: str) -> dict[str, Any]:
        with self._lock:
            if monotonic() >= self._expires_at or not self._keys:
                self._refresh()
            key = self._keys.get(kid)
            if key is not None:
                return key
            # Key rotation can introduce a new kid before the cache expires.
            self._refresh()
            key = self._keys.get(kid)
            if key is None:
                raise OIDCVerificationError("oidc_unknown_kid", "JWT signing key is unknown")
            return key


class OIDCTokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_provider: JWKSProvider,
        allowed_algorithms: tuple[str, ...] = ("RS256",),
        clock_skew_seconds: int = 60,
        required_scopes: frozenset[str] = frozenset(),
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_provider = jwks_provider
        self.allowed_algorithms = allowed_algorithms
        self.clock_skew_seconds = clock_skew_seconds
        self.required_scopes = required_scopes

    def verify(self, raw_token: str) -> AuthenticatedToken:
        if not raw_token:
            raise OIDCVerificationError("missing_token", "Bearer token is required")
        try:
            header = jwt.get_unverified_header(raw_token)
        except InvalidTokenError as exc:
            raise OIDCVerificationError("invalid_token_header", "JWT header is invalid") from exc

        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in self.allowed_algorithms:
            raise OIDCVerificationError("disallowed_algorithm", "JWT algorithm is not allowed")
        if not isinstance(kid, str) or not kid:
            raise OIDCVerificationError("missing_kid", "JWT key id is required")

        jwk_dict = self.jwks_provider.get_jwk(kid)
        if jwk_dict.get("use") not in {None, "sig"}:
            raise OIDCVerificationError("invalid_jwk_use", "JWK is not a signing key")
        if jwk_dict.get("alg") not in {None, algorithm}:
            raise OIDCVerificationError("jwk_algorithm_mismatch", "JWK algorithm does not match JWT")
        try:
            signing_key = PyJWK.from_dict(jwk_dict, algorithm=algorithm).key
            claims = jwt.decode(
                raw_token,
                key=signing_key,
                algorithms=list(self.allowed_algorithms),
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={
                    "require": ["exp", "iat", "iss", "sub", "aud"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except (InvalidTokenError, ValueError) as exc:
            raise OIDCVerificationError("invalid_token", "JWT verification failed") from exc

        scopes = self._extract_scopes(claims)
        missing_scopes = self.required_scopes - scopes
        if missing_scopes:
            raise OIDCVerificationError("missing_scope", "JWT does not contain required API scope")

        audience_claim = claims["aud"]
        audience = (
            tuple(audience_claim)
            if isinstance(audience_claim, list)
            else (str(audience_claim),)
        )
        return AuthenticatedToken(
            issuer=str(claims["iss"]),
            subject=str(claims["sub"]),
            audience=audience,
            issued_at=self._as_datetime(claims["iat"]),
            expires_at=self._as_datetime(claims["exp"]),
            not_before=self._as_datetime(claims["nbf"]) if "nbf" in claims else None,
            jwt_id=str(claims["jti"]) if claims.get("jti") else None,
            session_id=str(claims["sid"]) if claims.get("sid") else None,
            scopes=scopes,
            claims=dict(claims),
        )

    @staticmethod
    def _extract_scopes(claims: dict[str, Any]) -> frozenset[str]:
        raw_scope = claims.get("scope")
        if isinstance(raw_scope, str):
            return frozenset(part for part in raw_scope.split() if part)
        raw_scp = claims.get("scp")
        if isinstance(raw_scp, list):
            return frozenset(str(part) for part in raw_scp)
        if isinstance(raw_scp, str):
            return frozenset(part for part in raw_scp.split() if part)
        return frozenset()

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
