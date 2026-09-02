from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.access import (
    Permission,
    Principal,
    ROLE_PERMISSIONS,
    ResourceGrant,
    TenantStatus,
    UserRole,
)
from app.models.tenancy import OrganizationModel, ResourceGrantModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.db.session import set_tenant_context
from app.repositories.tenancy import MembershipRepository, ResourceGrantRepository, TenantRepository, UserAccountRepository
from app.schemas.tenancy import (
    MembershipCreate,
    OrganizationCreate,
    ResourceGrantCreate,
    TenantCreate,
    UserAccountCreate,
)


class TenancyInvariantError(ValueError):
    pass


class TenancyService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_tenant(self, payload: TenantCreate) -> TenantModel:
        repo = TenantRepository(self.session)
        if repo.get(payload.tenant_id):
            raise TenancyInvariantError("tenant already exists")
        tenant = TenantModel(
            tenant_id=payload.tenant_id,
            slug=payload.slug,
            display_name=payload.display_name,
            tenant_type=payload.tenant_type.value,
            status=TenantStatus.ACTIVE.value,
            data_region=payload.data_region,
        )
        self.session.add(tenant)
        self.session.flush()
        return tenant

    def create_organization(self, tenant_id: str, payload: OrganizationCreate) -> OrganizationModel:
        set_tenant_context(self.session, tenant_id)
        if not TenantRepository(self.session).get(tenant_id):
            raise TenancyInvariantError("tenant does not exist")
        if payload.parent_organization_id:
            parent = self.session.scalar(
                select(OrganizationModel).where(
                    OrganizationModel.organization_id == payload.parent_organization_id,
                    OrganizationModel.tenant_id == tenant_id,
                )
            )
            if parent is None:
                raise TenancyInvariantError("parent organization must belong to the same tenant")
        org = OrganizationModel(
            organization_id=payload.organization_id,
            tenant_id=tenant_id,
            parent_organization_id=payload.parent_organization_id,
            slug=payload.slug,
            display_name=payload.display_name,
            organization_type=payload.organization_type,
            external_identifiers=payload.external_identifiers,
        )
        self.session.add(org)
        self.session.flush()
        return org

    def create_user(self, payload: UserAccountCreate) -> UserAccountModel:
        repo = UserAccountRepository(self.session)
        if repo.get(payload.user_id):
            raise TenancyInvariantError("user already exists")
        return repo.add(
            UserAccountModel(
                user_id=payload.user_id,
                external_issuer=payload.external_issuer,
                external_subject=payload.external_subject,
                display_name=payload.display_name,
                email=payload.email,
                status=payload.status.value,
            )
        )

    def add_membership(self, tenant_id: str, payload: MembershipCreate) -> TenantMembershipModel:
        tenant = TenantRepository(self.session).get(tenant_id)
        user = UserAccountRepository(self.session).get(payload.user_id)
        if tenant is None:
            raise TenancyInvariantError("tenant does not exist")
        if user is None:
            raise TenancyInvariantError("user does not exist")
        if payload.organization_id:
            org = self.session.scalar(
                select(OrganizationModel).where(
                    OrganizationModel.organization_id == payload.organization_id,
                    OrganizationModel.tenant_id == tenant_id,
                    OrganizationModel.is_active.is_(True),
                )
            )
            if org is None:
                raise TenancyInvariantError("membership organization must belong to the tenant")
        repo = MembershipRepository(self.session, tenant_id)
        if repo.get_by_user(payload.user_id):
            raise TenancyInvariantError("user already has a membership in this tenant")
        return repo.add(
            TenantMembershipModel(
                membership_id=payload.membership_id,
                tenant_id=tenant_id,
                user_id=payload.user_id,
                role=payload.role.value,
                organization_id=payload.organization_id,
                status="active",
                patient_subject_id=payload.patient_subject_id,
                provider_organization_id=payload.provider_organization_id or payload.organization_id,
                invited_by_user_id=payload.invited_by_user_id,
                activated_at=datetime.now(timezone.utc),
            )
        )

    def create_resource_grant(
        self, owner_tenant_id: str, payload: ResourceGrantCreate
    ) -> ResourceGrantModel:
        if payload.grantee_tenant_id == owner_tenant_id:
            raise TenancyInvariantError("cross-tenant grant cannot target its owning tenant")
        tenant_repo = TenantRepository(self.session)
        owner = tenant_repo.get(owner_tenant_id)
        grantee = tenant_repo.get(payload.grantee_tenant_id)
        if owner is None or grantee is None:
            raise TenancyInvariantError("both owner and grantee tenants must exist")
        if owner.status != "active" or grantee.status != "active":
            raise TenancyInvariantError("resource grants require active owner and grantee tenants")
        actor = MembershipRepository(self.session, owner_tenant_id).get_by_user(
            payload.created_by_user_id
        )
        if actor is None or actor.status != "active":
            raise TenancyInvariantError("grant creator must be an active member of the owning tenant")
        if Permission.TENANT_GRANT_MANAGE not in ROLE_PERMISSIONS[UserRole(actor.role)]:
            raise TenancyInvariantError("grant creator is not permitted to manage resource grants")
        return ResourceGrantRepository(self.session, owner_tenant_id).add(
            ResourceGrantModel(
                grant_id=payload.grant_id,
                owner_tenant_id=owner_tenant_id,
                grantee_tenant_id=payload.grantee_tenant_id,
                resource_type=payload.resource_type.value,
                resource_id=payload.resource_id,
                permissions=sorted(permission.value for permission in payload.permissions),
                starts_at=payload.starts_at,
                expires_at=payload.expires_at,
                created_by_user_id=payload.created_by_user_id,
            )
        )

    def revoke_resource_grant(
        self,
        owner_tenant_id: str,
        grant_id: str,
        *,
        revoked_by_user_id: str,
        reason: str,
    ) -> ResourceGrantModel:
        actor = MembershipRepository(self.session, owner_tenant_id).get_by_user(
            revoked_by_user_id
        )
        if actor is None or actor.status != "active":
            raise TenancyInvariantError("grant revoker must be an active member of the owning tenant")
        if Permission.TENANT_GRANT_MANAGE not in ROLE_PERMISSIONS[UserRole(actor.role)]:
            raise TenancyInvariantError("grant revoker is not permitted to manage resource grants")
        repo = ResourceGrantRepository(self.session, owner_tenant_id)
        grant = repo.get(grant_id)
        if grant is None:
            raise TenancyInvariantError("resource grant does not exist in this tenant")
        if not grant.is_active:
            return grant
        return repo.revoke(
            grant,
            revoked_by_user_id=revoked_by_user_id,
            reason=reason,
        )



class PrincipalResolver:
    """Build authorization principals only from persisted server-side identity state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve(self, *, user_id: str, tenant_id: str) -> Principal | None:
        tenant = TenantRepository(self.session).get(tenant_id)
        user = UserAccountRepository(self.session).get(user_id)
        membership = MembershipRepository(self.session, tenant_id).get_by_user(user_id)
        if tenant is None or user is None or membership is None:
            return None
        is_active = tenant.status == "active" and user.status == "active" and membership.status == "active"
        return Principal(
            user_id=user_id,
            tenant_id=tenant_id,
            role=membership.role,
            is_active=is_active,
            patient_subject_id=membership.patient_subject_id,
            provider_organization_id=membership.provider_organization_id,
        )

    def resolve_external_identity(
        self, *, issuer: str, external_subject: str, tenant_id: str
    ) -> Principal | None:
        user = UserAccountRepository(self.session).get_by_external_identity(
            issuer=issuer, external_subject=external_subject
        )
        if user is None:
            return None
        return self.resolve(user_id=user.user_id, tenant_id=tenant_id)


class ResourceGrantResolver:
    def __init__(self, session: Session) -> None:
        self.session = session

    def for_resource(
        self, *, owner_tenant_id: str, resource_type: str, resource_id: str
    ) -> tuple[ResourceGrant, ...]:
        models = ResourceGrantRepository(self.session, owner_tenant_id).list_effective_for_resource(
            resource_type, resource_id
        )
        resolved: list[ResourceGrant] = []
        for model in models:
            valid_permissions = frozenset(
                Permission(permission)
                for permission in model.permissions
                if permission in Permission._value2member_map_
            )
            if not valid_permissions:
                continue
            resolved.append(
                ResourceGrant(
                    grant_id=model.grant_id,
                    grantee_tenant_id=model.grantee_tenant_id,
                    permissions=valid_permissions,
                    is_active=model.is_active,
                )
            )
        return tuple(resolved)
