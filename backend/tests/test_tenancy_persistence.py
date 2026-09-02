from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.access import AccountStatus, Permission, ResourceType, TenantType, UserRole
from app.repositories.tenancy import MembershipRepository, ResourceGrantRepository
from app.schemas.tenancy import (
    MembershipCreate,
    OrganizationCreate,
    ResourceGrantCreate,
    TenantCreate,
    UserAccountCreate,
)
from app.services.tenancy import PrincipalResolver, ResourceGrantResolver, TenancyInvariantError, TenancyService


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    Base.metadata.drop_all(engine)


def create_tenant(service: TenancyService, tenant_id: str, slug: str) -> None:
    service.create_tenant(
        TenantCreate(
            tenant_id=tenant_id,
            slug=slug,
            display_name=slug.replace("-", " ").title(),
            tenant_type=TenantType.PAYER,
        )
    )


def create_user(
    service: TenancyService,
    user_id: str,
    *,
    status: AccountStatus = AccountStatus.ACTIVE,
) -> None:
    service.create_user(
        UserAccountCreate(
            user_id=user_id,
            external_subject=f"oidc|{user_id}",
            display_name=user_id,
            status=status,
        )
    )


def add_admin(service: TenancyService, tenant_id: str, user_id: str) -> None:
    service.add_membership(
        tenant_id,
        MembershipCreate(
            membership_id=f"membership-{tenant_id}-{user_id}",
            user_id=user_id,
            role=UserRole.TENANT_ADMIN,
        ),
    )


def test_persists_tenant_organization_user_and_membership(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-payer-a", "payer-a")
    create_user(service, "reviewer-001")
    service.create_organization(
        "tenant-payer-a",
        OrganizationCreate(
            organization_id="org-claims",
            slug="claims-operations",
            display_name="Claims Operations",
            organization_type="payer",
        ),
    )
    membership = service.add_membership(
        "tenant-payer-a",
        MembershipCreate(
            membership_id="membership-reviewer-001",
            user_id="reviewer-001",
            role=UserRole.CLAIMS_REVIEWER,
            organization_id="org-claims",
        ),
    )

    assert membership.tenant_id == "tenant-payer-a"
    assert membership.organization_id == "org-claims"
    assert MembershipRepository(session, "tenant-payer-a").get("membership-reviewer-001") is not None


def test_repository_cannot_read_membership_from_another_tenant(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-a", "tenant-a")
    create_tenant(service, "tenant-b", "tenant-b")
    create_user(service, "user-001")
    service.add_membership(
        "tenant-a",
        MembershipCreate(
            membership_id="membership-001",
            user_id="user-001",
            role=UserRole.CLAIMS_REVIEWER,
        ),
    )

    assert MembershipRepository(session, "tenant-b").get("membership-001") is None


def test_membership_rejects_organization_from_another_tenant(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-a", "tenant-a")
    create_tenant(service, "tenant-b", "tenant-b")
    create_user(service, "provider-user")
    service.create_organization(
        "tenant-b",
        OrganizationCreate(
            organization_id="provider-b",
            slug="provider-b",
            display_name="Provider B",
            organization_type="provider",
        ),
    )

    with pytest.raises(TenancyInvariantError, match="organization must belong"):
        service.add_membership(
            "tenant-a",
            MembershipCreate(
                membership_id="membership-provider",
                user_id="provider-user",
                role=UserRole.PROVIDER,
                organization_id="provider-b",
            ),
        )


def test_role_scope_validation_requires_patient_identity() -> None:
    with pytest.raises(ValidationError, match="patient_subject_id"):
        MembershipCreate(
            membership_id="membership-patient",
            user_id="patient-user",
            role=UserRole.PATIENT,
        )


def test_principal_is_resolved_only_from_persisted_active_state(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-a", "tenant-a")
    create_user(service, "patient-user", status=AccountStatus.ACTIVE)
    service.add_membership(
        "tenant-a",
        MembershipCreate(
            membership_id="membership-patient",
            user_id="patient-user",
            role=UserRole.PATIENT,
            patient_subject_id="patient-001",
        ),
    )

    principal = PrincipalResolver(session).resolve(user_id="patient-user", tenant_id="tenant-a")

    assert principal is not None
    assert principal.is_active is True
    assert principal.patient_subject_id == "patient-001"
    assert principal.role is UserRole.PATIENT


def test_resource_grant_lifecycle_is_persistent_permission_scoped_and_revocable(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-owner", "tenant-owner")
    create_tenant(service, "tenant-grantee", "tenant-grantee")
    create_user(service, "tenant-admin")
    add_admin(service, "tenant-owner", "tenant-admin")

    grant = service.create_resource_grant(
        "tenant-owner",
        ResourceGrantCreate(
            grant_id="grant-001",
            grantee_tenant_id="tenant-grantee",
            resource_type=ResourceType.CLAIM,
            resource_id="claim-001",
            permissions=frozenset({Permission.CLAIM_READ}),
            created_by_user_id="tenant-admin",
        ),
    )

    effective = ResourceGrantRepository(session, "tenant-owner").list_effective_for_resource(
        "claim", "claim-001"
    )
    resolved = ResourceGrantResolver(session).for_resource(
        owner_tenant_id="tenant-owner", resource_type="claim", resource_id="claim-001"
    )

    assert effective == [grant]
    assert resolved[0].permissions == frozenset({Permission.CLAIM_READ})

    service.revoke_resource_grant(
        "tenant-owner", "grant-001", revoked_by_user_id="tenant-admin", reason="case closed"
    )

    assert ResourceGrantRepository(session, "tenant-owner").list_effective_for_resource(
        "claim", "claim-001"
    ) == []
    assert grant.revoked_at is not None
    assert grant.revocation_reason == "case closed"


def test_resource_grant_creator_must_have_tenant_grant_permission(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-owner", "tenant-owner")
    create_tenant(service, "tenant-grantee", "tenant-grantee")
    create_user(service, "reviewer")
    service.add_membership(
        "tenant-owner",
        MembershipCreate(
            membership_id="membership-reviewer",
            user_id="reviewer",
            role=UserRole.CLAIMS_REVIEWER,
        ),
    )

    with pytest.raises(TenancyInvariantError, match="not permitted"):
        service.create_resource_grant(
            "tenant-owner",
            ResourceGrantCreate(
                grant_id="grant-denied",
                grantee_tenant_id="tenant-grantee",
                resource_type=ResourceType.CLAIM,
                resource_id="claim-001",
                permissions=frozenset({Permission.CLAIM_READ}),
                created_by_user_id="reviewer",
            ),
        )


def test_expired_and_future_resource_grants_are_not_effective(session: Session) -> None:
    service = TenancyService(session)
    create_tenant(service, "tenant-owner", "tenant-owner")
    create_tenant(service, "tenant-grantee", "tenant-grantee")
    create_user(service, "tenant-admin")
    add_admin(service, "tenant-owner", "tenant-admin")
    now = datetime.now(timezone.utc)

    for grant_id, starts_at, expires_at in (
        ("expired", now - timedelta(days=2), now - timedelta(days=1)),
        ("future", now + timedelta(days=1), now + timedelta(days=2)),
    ):
        service.create_resource_grant(
            "tenant-owner",
            ResourceGrantCreate(
                grant_id=grant_id,
                grantee_tenant_id="tenant-grantee",
                resource_type=ResourceType.CLAIM,
                resource_id="claim-001",
                permissions=frozenset({Permission.CLAIM_READ}),
                starts_at=starts_at,
                expires_at=expires_at,
                created_by_user_id="tenant-admin",
            ),
        )

    effective = ResourceGrantRepository(session, "tenant-owner").list_effective_for_resource(
        "claim", "claim-001", at=now
    )
    assert effective == []
