from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.tenancy import ResourceGrantModel, TenantMembershipModel, TenantModel, UserAccountModel


class TenantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, tenant_id: str) -> TenantModel | None:
        return self.session.get(TenantModel, tenant_id)

    def list_active(self) -> list[TenantModel]:
        return list(
            self.session.scalars(
                select(TenantModel).where(TenantModel.status == "active").order_by(TenantModel.tenant_id)
            )
        )


class MembershipRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def get(self, membership_id: str) -> TenantMembershipModel | None:
        return self.session.scalar(
            select(TenantMembershipModel).where(
                TenantMembershipModel.membership_id == membership_id,
                TenantMembershipModel.tenant_id == self.tenant_id,
            )
        )

    def get_by_user(self, user_id: str) -> TenantMembershipModel | None:
        return self.session.scalar(
            select(TenantMembershipModel).where(
                TenantMembershipModel.user_id == user_id,
                TenantMembershipModel.tenant_id == self.tenant_id,
            )
        )

    def list(self) -> list[TenantMembershipModel]:
        return list(
            self.session.scalars(
                select(TenantMembershipModel)
                .where(TenantMembershipModel.tenant_id == self.tenant_id)
                .order_by(TenantMembershipModel.membership_id)
            )
        )

    def add(self, membership: TenantMembershipModel) -> TenantMembershipModel:
        if membership.tenant_id != self.tenant_id:
            raise ValueError("membership tenant does not match repository tenant context")
        self.session.add(membership)
        self.session.flush()
        return membership


class UserAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: str) -> UserAccountModel | None:
        return self.session.get(UserAccountModel, user_id)

    def get_by_external_identity(
        self, *, issuer: str, external_subject: str
    ) -> UserAccountModel | None:
        return self.session.scalar(
            select(UserAccountModel).where(
                UserAccountModel.external_issuer == issuer,
                UserAccountModel.external_subject == external_subject,
            )
        )

    def add(self, user: UserAccountModel) -> UserAccountModel:
        self.session.add(user)
        self.session.flush()
        return user


class ResourceGrantRepository:
    def __init__(self, session: Session, owner_tenant_id: str) -> None:
        self.session = session
        self.owner_tenant_id = owner_tenant_id
        set_tenant_context(session, owner_tenant_id)

    def add(self, grant: ResourceGrantModel) -> ResourceGrantModel:
        if grant.owner_tenant_id != self.owner_tenant_id:
            raise ValueError("grant owner tenant does not match repository tenant context")
        self.session.add(grant)
        self.session.flush()
        return grant

    def get(self, grant_id: str) -> ResourceGrantModel | None:
        return self.session.scalar(
            select(ResourceGrantModel).where(
                ResourceGrantModel.grant_id == grant_id,
                ResourceGrantModel.owner_tenant_id == self.owner_tenant_id,
            )
        )

    def list_for_resource(self, resource_type: str, resource_id: str) -> list[ResourceGrantModel]:
        return list(
            self.session.scalars(
                select(ResourceGrantModel)
                .where(
                    ResourceGrantModel.owner_tenant_id == self.owner_tenant_id,
                    ResourceGrantModel.resource_type == resource_type,
                    ResourceGrantModel.resource_id == resource_id,
                )
                .order_by(ResourceGrantModel.grant_id)
            )
        )

    def list_effective_for_resource(
        self, resource_type: str, resource_id: str, *, at: datetime | None = None
    ) -> list[ResourceGrantModel]:
        at = at or datetime.now(timezone.utc)
        return list(
            self.session.scalars(
                select(ResourceGrantModel)
                .where(
                    ResourceGrantModel.owner_tenant_id == self.owner_tenant_id,
                    ResourceGrantModel.resource_type == resource_type,
                    ResourceGrantModel.resource_id == resource_id,
                    ResourceGrantModel.is_active.is_(True),
                    or_(ResourceGrantModel.starts_at.is_(None), ResourceGrantModel.starts_at <= at),
                    or_(ResourceGrantModel.expires_at.is_(None), ResourceGrantModel.expires_at > at),
                    ResourceGrantModel.revoked_at.is_(None),
                )
                .order_by(ResourceGrantModel.grant_id)
            )
        )

    def revoke(
        self,
        grant: ResourceGrantModel,
        *,
        revoked_by_user_id: str,
        reason: str,
        at: datetime | None = None,
    ) -> ResourceGrantModel:
        if grant.owner_tenant_id != self.owner_tenant_id:
            raise ValueError("cannot revoke a grant owned by another tenant")
        grant.is_active = False
        grant.revoked_at = at or datetime.now(timezone.utc)
        grant.revoked_by_user_id = revoked_by_user_id
        grant.revocation_reason = reason
        self.session.flush()
        return grant


class SharedGrantLookupRepository:
    """Read-only lookup for grants visible to an authenticated grantee tenant.

    The explicit grantee predicate is retained even when PostgreSQL RLS is active.
    """

    def __init__(self, session: Session, grantee_tenant_id: str) -> None:
        self.session = session
        self.grantee_tenant_id = grantee_tenant_id
        set_tenant_context(session, grantee_tenant_id)

    def list_effective(self, *, at: datetime | None = None) -> list[ResourceGrantModel]:
        at = at or datetime.now(timezone.utc)
        return list(
            self.session.scalars(
                select(ResourceGrantModel).where(
                    ResourceGrantModel.grantee_tenant_id == self.grantee_tenant_id,
                    ResourceGrantModel.is_active.is_(True),
                    or_(ResourceGrantModel.starts_at.is_(None), ResourceGrantModel.starts_at <= at),
                    or_(ResourceGrantModel.expires_at.is_(None), ResourceGrantModel.expires_at > at),
                    ResourceGrantModel.revoked_at.is_(None),
                )
            )
        )
