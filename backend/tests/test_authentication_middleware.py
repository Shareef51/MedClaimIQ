from __future__ import annotations

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app
from app.models.authentication import AuthenticationSessionModel  # noqa: F401
from app.models.tenancy import TenantMembershipModel, TenantModel, UserAccountModel
from app.security.authentication import AuthenticationService
from app.security.oidc import OIDCTokenVerifier, OIDCVerificationError


ISSUER = "https://identity.integration.test"
SECRET = "integration-session-secret-that-is-definitely-long-enough"


class StaticJWKSProvider:
    def __init__(self, jwk: dict[str, object]) -> None:
        self.jwk = jwk

    def get_jwk(self, kid: str) -> dict[str, object]:
        if kid != self.jwk["kid"]:
            raise OIDCVerificationError("oidc_unknown_kid", "unknown kid")
        return self.jwk


def setup_app_state():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        for tenant_id in ("tenant-a", "tenant-b"):
            db.add(
                TenantModel(
                    tenant_id=tenant_id,
                    slug=tenant_id,
                    display_name=tenant_id,
                    tenant_type="demo",
                    status="active",
                    data_region="local",
                )
            )
        db.add(
            UserAccountModel(
                user_id="reviewer-1",
                external_issuer=ISSUER,
                external_subject="subject-1",
                display_name="Reviewer One",
                email="reviewer@example.test",
                status="active",
            )
        )
        db.add(
            TenantMembershipModel(
                membership_id="membership-1",
                tenant_id="tenant-a",
                user_id="reviewer-1",
                role="claims_reviewer",
                status="active",
            )
        )
        db.commit()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raw_jwk = RSAAlgorithm.to_jwk(private_key.public_key())
    jwk = json.loads(raw_jwk) if isinstance(raw_jwk, str) else dict(raw_jwk)
    jwk.update({"kid": "integration-key", "use": "sig", "alg": "RS256"})
    verifier = OIDCTokenVerifier(
        issuer=ISSUER,
        audience="medclaimiq-api",
        jwks_provider=StaticJWKSProvider(jwk),
        required_scopes=frozenset({"medclaimiq.api"}),
    )
    app.state.authentication_service = AuthenticationService(
        token_verifier=verifier,
        session_hmac_secret=SECRET,
        session_required=True,
    )
    app.state.session_factory_provider = lambda: factory
    return private_key


def mint(private_key) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": ISSUER,
            "sub": "subject-1",
            "aud": "medclaimiq-api",
            "iat": now,
            "exp": now + 600,
            "sid": "session-1",
            "jti": "jti-1",
            "scope": "medclaimiq.api",
            # Deliberately malicious/untrusted authorization hints. They must not
            # override persisted membership or the verified tenant selector.
            "tenant_id": "tenant-b",
            "role": "system_admin",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "integration-key"},
    )


def test_protected_route_requires_bearer_token() -> None:
    setup_app_state()
    response = TestClient(app).get("/api/v1/auth/me", headers={"X-Tenant-Id": "tenant-a"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_bearer_token"
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_route_requires_tenant_selector() -> None:
    private_key = setup_app_state()
    response = TestClient(app).get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {mint(private_key)}"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_tenant_context"


def test_tenant_and_role_are_resolved_from_persistence_not_token_claims() -> None:
    private_key = setup_app_state()
    response = TestClient(app).get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {mint(private_key)}",
            "X-Tenant-Id": "tenant-a",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "tenant-a"
    assert body["role"] == "claims_reviewer"
    assert body["user_id"] == "reviewer-1"
    assert body["application_session_id"].startswith("as_")
    assert response.headers["cache-control"] == "no-store"


def test_header_cannot_select_tenant_without_persisted_membership() -> None:
    private_key = setup_app_state()
    response = TestClient(app).get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {mint(private_key)}",
            "X-Tenant-Id": "tenant-b",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "identity_not_mapped"
