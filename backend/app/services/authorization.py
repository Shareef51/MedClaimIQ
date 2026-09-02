from __future__ import annotations

from app.domain.access import (
    AccessDecision,
    AccessReason,
    AccessRequest,
    Permission,
    ResourceType,
    ROLE_PERMISSIONS,
    TenantStatus,
    UserRole,
)


_SYSTEM_RESOURCE_TYPES = {ResourceType.TENANT, ResourceType.SYSTEM_HEALTH}
_REVIEWER_ASSIGNMENT_PERMISSIONS = {
    Permission.CLAIM_REVIEW,
    Permission.CLAIM_EDIT_AI_RECOMMENDATION,
    Permission.CLAIM_RECORD_HUMAN_DECISION,
}
_PATIENT_SCOPED_TYPES = {ResourceType.CLAIM, ResourceType.EVIDENCE}
_PROVIDER_SCOPED_TYPES = {
    ResourceType.CLAIM,
    ResourceType.EVIDENCE,
    ResourceType.HOSPITAL_RECORD,
}


def _allow(reason: AccessReason) -> AccessDecision:
    return AccessDecision(allowed=True, reason=reason)


def _deny(reason: AccessReason) -> AccessDecision:
    return AccessDecision(allowed=False, reason=reason)


class AuthorizationService:
    """Deny-first RBAC + ABAC authorization policy.

    Caller responsibility:
    - `principal` must come from verified authentication/session state.
    - `resource` and explicit grants must come from server-side persistence.
    - client-supplied ownership/grant attributes must never be trusted directly.
    """

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        principal = request.principal
        resource = request.resource

        if not principal.is_active:
            return _deny(AccessReason.DENY_INACTIVE_PRINCIPAL)

        if request.tenant_status is not TenantStatus.ACTIVE:
            return _deny(AccessReason.DENY_TENANT_INACTIVE)

        if request.permission not in ROLE_PERMISSIONS[principal.role]:
            return _deny(AccessReason.DENY_PERMISSION_NOT_IN_ROLE)

        if principal.role is UserRole.SYSTEM_ADMIN:
            if resource.resource_type in _SYSTEM_RESOURCE_TYPES:
                return _allow(AccessReason.ALLOW_SYSTEM_SCOPE)
            return _deny(AccessReason.DENY_RESOURCE_SCOPE)

        same_tenant = principal.tenant_id == resource.owner_tenant_id
        explicit_cross_tenant_grant = any(
            grant.is_active
            and grant.grantee_tenant_id == principal.tenant_id
            and request.permission in grant.permissions
            for grant in resource.cross_tenant_grants
        )
        if not same_tenant and not explicit_cross_tenant_grant:
            return _deny(AccessReason.DENY_CROSS_TENANT)

        if principal.role is UserRole.PATIENT and resource.resource_type in _PATIENT_SCOPED_TYPES:
            if (
                principal.patient_subject_id is None
                or resource.owner_patient_subject_id != principal.patient_subject_id
            ):
                return _deny(AccessReason.DENY_PATIENT_NOT_OWNER)
            return _allow(
                AccessReason.ALLOW_PATIENT_OWNERSHIP
                if same_tenant
                else AccessReason.ALLOW_EXPLICIT_TENANT_GRANT
            )

        if principal.role in {UserRole.PROVIDER, UserRole.HOSPITAL_ADMIN} and (
            resource.resource_type in _PROVIDER_SCOPED_TYPES
        ):
            if (
                principal.provider_organization_id is None
                or resource.related_provider_organization_id != principal.provider_organization_id
            ):
                return _deny(AccessReason.DENY_PROVIDER_NOT_RELATED)
            return _allow(
                AccessReason.ALLOW_PROVIDER_RELATIONSHIP
                if same_tenant
                else AccessReason.ALLOW_EXPLICIT_TENANT_GRANT
            )

        if (
            principal.role is UserRole.CLAIMS_REVIEWER
            and request.permission in _REVIEWER_ASSIGNMENT_PERMISSIONS
            and resource.assigned_reviewer_user_id not in {None, principal.user_id}
        ):
            return _deny(AccessReason.DENY_REVIEWER_NOT_ASSIGNED)

        if explicit_cross_tenant_grant and not same_tenant:
            return _allow(AccessReason.ALLOW_EXPLICIT_TENANT_GRANT)

        return _allow(
            AccessReason.ALLOW_ASSIGNED_REVIEWER
            if principal.role is UserRole.CLAIMS_REVIEWER
            and request.permission in _REVIEWER_ASSIGNMENT_PERMISSIONS
            else AccessReason.ALLOW_ROLE_PERMISSION
        )


authorization_service = AuthorizationService()
