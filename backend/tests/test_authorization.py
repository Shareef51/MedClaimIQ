import pytest

from app.domain.access import (
    AccessReason,
    AccessRequest,
    Permission,
    Principal,
    ResourceAccessContext,
    ResourceGrant,
    ResourceType,
    TenantStatus,
    UserRole,
)
from app.services.authorization import AuthorizationService


authz = AuthorizationService()


def resource(**overrides: object) -> ResourceAccessContext:
    values: dict[str, object] = {
        "resource_type": ResourceType.CLAIM,
        "resource_id": "claim-001",
        "owner_tenant_id": "tenant-payer-a",
        "owner_patient_subject_id": "patient-001",
        "related_provider_organization_id": "provider-001",
        "assigned_reviewer_user_id": "reviewer-001",
    }
    values.update(overrides)
    return ResourceAccessContext(**values)


def principal(role: UserRole, **overrides: object) -> Principal:
    values: dict[str, object] = {
        "user_id": "reviewer-001",
        "tenant_id": "tenant-payer-a",
        "role": role,
    }
    values.update(overrides)
    return Principal(**values)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (UserRole.PATIENT, Permission.CLAIM_REVIEW),
        (UserRole.AUDITOR, Permission.CLAIM_UPDATE),
        (UserRole.TENANT_ADMIN, Permission.CLAIM_READ),
        (UserRole.SYSTEM_ADMIN, Permission.CLAIM_READ),
    ],
)
def test_role_without_permission_is_denied(role: UserRole, permission: Permission) -> None:
    decision = authz.evaluate(
        AccessRequest(principal=principal(role), permission=permission, resource=resource())
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_PERMISSION_NOT_IN_ROLE


def test_cross_tenant_is_denied_by_default() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, tenant_id="tenant-other"),
            permission=Permission.CLAIM_READ,
            resource=resource(),
        )
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_CROSS_TENANT


def test_explicit_cross_tenant_grant_allows_permitted_operation() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, tenant_id="tenant-other"),
            permission=Permission.CLAIM_READ,
            resource=resource(
                cross_tenant_grants=(
                    ResourceGrant(
                        grant_id="grant-001",
                        grantee_tenant_id="tenant-other",
                        permissions=frozenset({Permission.CLAIM_READ}),
                    ),
                )
            ),
        )
    )

    assert decision.allowed is True
    assert decision.reason is AccessReason.ALLOW_EXPLICIT_TENANT_GRANT


def test_patient_can_read_only_own_claim() -> None:
    own = authz.evaluate(
        AccessRequest(
            principal=principal(
                UserRole.PATIENT,
                user_id="patient-user-001",
                patient_subject_id="patient-001",
            ),
            permission=Permission.CLAIM_READ,
            resource=resource(),
        )
    )
    other = authz.evaluate(
        AccessRequest(
            principal=principal(
                UserRole.PATIENT,
                user_id="patient-user-001",
                patient_subject_id="patient-999",
            ),
            permission=Permission.CLAIM_READ,
            resource=resource(),
        )
    )

    assert own.allowed is True
    assert own.reason is AccessReason.ALLOW_PATIENT_OWNERSHIP
    assert other.allowed is False
    assert other.reason is AccessReason.DENY_PATIENT_NOT_OWNER


def test_provider_requires_resource_relationship() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(
                UserRole.PROVIDER,
                user_id="provider-user-001",
                provider_organization_id="provider-other",
            ),
            permission=Permission.CLAIM_READ,
            resource=resource(),
        )
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_PROVIDER_NOT_RELATED


def test_reviewer_cannot_record_human_decision_on_someone_elses_assignment() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, user_id="reviewer-002"),
            permission=Permission.CLAIM_RECORD_HUMAN_DECISION,
            resource=resource(assigned_reviewer_user_id="reviewer-001"),
        )
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_REVIEWER_NOT_ASSIGNED


def test_system_admin_can_manage_system_tenant_but_not_claims() -> None:
    system_resource = resource(
        resource_type=ResourceType.TENANT,
        resource_id="tenant-payer-a",
    )
    allowed = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.SYSTEM_ADMIN),
            permission=Permission.SYSTEM_TENANT_MANAGE,
            resource=system_resource,
        )
    )

    assert allowed.allowed is True
    assert allowed.reason is AccessReason.ALLOW_SYSTEM_SCOPE


def test_inactive_principal_and_suspended_tenant_are_denied() -> None:
    inactive = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, is_active=False),
            permission=Permission.CLAIM_READ,
            resource=resource(),
        )
    )
    suspended = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER),
            permission=Permission.CLAIM_READ,
            resource=resource(),
            tenant_status=TenantStatus.SUSPENDED,
        )
    )

    assert inactive.reason is AccessReason.DENY_INACTIVE_PRINCIPAL
    assert suspended.reason is AccessReason.DENY_TENANT_INACTIVE


def test_cross_tenant_grant_is_permission_scoped() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, tenant_id="tenant-other"),
            permission=Permission.CLAIM_REVIEW,
            resource=resource(
                cross_tenant_grants=(
                    ResourceGrant(
                        grant_id="grant-read-only",
                        grantee_tenant_id="tenant-other",
                        permissions=frozenset({Permission.CLAIM_READ}),
                    ),
                )
            ),
        )
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_CROSS_TENANT


def test_inactive_cross_tenant_grant_is_denied() -> None:
    decision = authz.evaluate(
        AccessRequest(
            principal=principal(UserRole.CLAIMS_REVIEWER, tenant_id="tenant-other"),
            permission=Permission.CLAIM_READ,
            resource=resource(
                cross_tenant_grants=(
                    ResourceGrant(
                        grant_id="grant-revoked",
                        grantee_tenant_id="tenant-other",
                        permissions=frozenset({Permission.CLAIM_READ}),
                        is_active=False,
                    ),
                )
            ),
        )
    )

    assert decision.allowed is False
    assert decision.reason is AccessReason.DENY_CROSS_TENANT
