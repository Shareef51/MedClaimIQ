from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.authentication import AuthenticationSessionModel  # noqa: F401
from app.models.tenancy import TenantMembershipModel, TenantModel, UserAccountModel
from app.security.oidc import AuthenticatedToken
from app.security.session import AuthenticationSessionService, SessionSecurityError
from app.services.tenancy import PrincipalResolver


SECRET = "test-session-hmac-secret-that-is-long-enough-123456"
ISSUER_A = "https://issuer-a.example"
ISSUER_B = "https://issuer-b.example"


def new_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def add_identity(db: Session, *, issuer: str, user_id: str, tenant_id: str, subject: str) -> None:
    if db.get(TenantModel, tenant_id) is None:
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
            user_id=user_id,
            external_issuer=issuer,
            external_subject=subject,
            display_name=user_id,
            email=f"{user_id}@example.test",
            status="active",
        )
    )
    db.add(
        TenantMembershipModel(
            membership_id=f"m-{user_id}-{tenant_id}",
            tenant_id=tenant_id,
            user_id=user_id,
            role="claims_reviewer",
            status="active",
            activated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def token(*, issuer: str = ISSUER_A, subject: str = "shared-subject") -> AuthenticatedToken:
    now = datetime.now(timezone.utc)
    return AuthenticatedToken(
        issuer=issuer,
        subject=subject,
        audience=("medclaimiq-api",),
        issued_at=now,
        expires_at=now + timedelta(minutes=10),
        not_before=None,
        jwt_id="raw-jti-value",
        session_id="raw-oidc-session-value",
        scopes=frozenset({"medclaimiq.api"}),
        claims={},
    )


def test_issuer_and_subject_form_external_identity_key() -> None:
    db = new_session()
    add_identity(db, issuer=ISSUER_A, user_id="user-a", tenant_id="tenant-a", subject="same-sub")
    add_identity(db, issuer=ISSUER_B, user_id="user-b", tenant_id="tenant-b", subject="same-sub")

    resolver = PrincipalResolver(db)
    principal_a = resolver.resolve_external_identity(
        issuer=ISSUER_A, external_subject="same-sub", tenant_id="tenant-a"
    )
    principal_b = resolver.resolve_external_identity(
        issuer=ISSUER_B, external_subject="same-sub", tenant_id="tenant-b"
    )
    assert principal_a is not None and principal_a.user_id == "user-a"
    assert principal_b is not None and principal_b.user_id == "user-b"


def test_session_persistence_hashes_external_session_and_jti() -> None:
    db = new_session()
    add_identity(db, issuer=ISSUER_A, user_id="user-a", tenant_id="tenant-a", subject="shared-subject")
    service = AuthenticationSessionService(db, hmac_secret=SECRET)
    auth_session = service.validate_or_create(
        token=token(), user_id="user-a", tenant_id="tenant-a", client_fingerprint="client"
    )
    db.commit()

    assert auth_session.external_session_hash != "raw-oidc-session-value"
    assert auth_session.token_jti_hash != "raw-jti-value"
    assert len(auth_session.external_session_hash) == 64
    assert len(auth_session.token_jti_hash or "") == 64


def test_revoked_session_cannot_be_reused() -> None:
    db = new_session()
    add_identity(db, issuer=ISSUER_A, user_id="user-a", tenant_id="tenant-a", subject="shared-subject")
    service = AuthenticationSessionService(db, hmac_secret=SECRET)
    auth_session = service.validate_or_create(
        token=token(), user_id="user-a", tenant_id="tenant-a"
    )
    service.revoke(
        tenant_id="tenant-a",
        session_id=auth_session.session_id,
        revoked_by_user_id="user-a",
        reason="user logout",
    )
    db.commit()

    with pytest.raises(SessionSecurityError, match="revoked"):
        service.validate_or_create(token=token(), user_id="user-a", tenant_id="tenant-a")
