from __future__ import annotations

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.security.oidc import OIDCTokenVerifier, OIDCVerificationError


ISSUER = "https://identity.test.example"
AUDIENCE = "medclaimiq-api"


class StaticJWKSProvider:
    def __init__(self, jwk: dict[str, object]) -> None:
        self.jwk = jwk

    def get_jwk(self, kid: str) -> dict[str, object]:
        if kid != self.jwk["kid"]:
            raise OIDCVerificationError("oidc_unknown_kid", "unknown kid")
        return self.jwk


def make_signing_material() -> tuple[object, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raw_jwk = RSAAlgorithm.to_jwk(private_key.public_key())
    jwk = json.loads(raw_jwk) if isinstance(raw_jwk, str) else dict(raw_jwk)
    jwk.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    return private_key, jwk


def mint(private_key, **overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "sub": "subject-123",
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 600,
        "sid": "oidc-session-1",
        "jti": "token-jti-1",
        "scope": "openid medclaimiq.api",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def verifier(jwk: dict[str, object]) -> OIDCTokenVerifier:
    return OIDCTokenVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_provider=StaticJWKSProvider(jwk),
        required_scopes=frozenset({"medclaimiq.api"}),
    )


def test_valid_signed_token_is_normalized() -> None:
    private_key, jwk = make_signing_material()
    token = verifier(jwk).verify(mint(private_key))
    assert token.issuer == ISSUER
    assert token.subject == "subject-123"
    assert token.session_id == "oidc-session-1"
    assert "medclaimiq.api" in token.scopes


def test_wrong_audience_is_rejected() -> None:
    private_key, jwk = make_signing_material()
    with pytest.raises(OIDCVerificationError) as exc:
        verifier(jwk).verify(mint(private_key, aud="different-api"))
    assert exc.value.code == "invalid_token"


def test_wrong_issuer_is_rejected() -> None:
    private_key, jwk = make_signing_material()
    with pytest.raises(OIDCVerificationError) as exc:
        verifier(jwk).verify(mint(private_key, iss="https://attacker.example"))
    assert exc.value.code == "invalid_token"


def test_required_api_scope_is_enforced() -> None:
    private_key, jwk = make_signing_material()
    with pytest.raises(OIDCVerificationError) as exc:
        verifier(jwk).verify(mint(private_key, scope="openid profile"))
    assert exc.value.code == "missing_scope"
