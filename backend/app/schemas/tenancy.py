from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.access import AccountStatus, Permission, ResourceType, TenantStatus, TenantType, UserRole


class TenantCreate(BaseModel):
    tenant_id: str = Field(min_length=3, max_length=64)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    display_name: str = Field(min_length=2, max_length=160)
    tenant_type: TenantType
    data_region: str = Field(default="local", min_length=2, max_length=32)


class OrganizationCreate(BaseModel):
    organization_id: str = Field(min_length=3, max_length=128)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    display_name: str = Field(min_length=2, max_length=180)
    organization_type: str = Field(
        pattern=r"^(payer|provider|hospital|department|third_party_administrator)$"
    )
    parent_organization_id: str | None = None
    external_identifiers: dict[str, str] = Field(default_factory=dict)


class UserAccountCreate(BaseModel):
    user_id: str = Field(min_length=3, max_length=128)
    external_issuer: str = Field(default="https://identity.local.medclaimiq", min_length=8, max_length=512)
    external_subject: str = Field(min_length=3, max_length=256)
    display_name: str = Field(min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    status: AccountStatus = AccountStatus.INVITED


class MembershipCreate(BaseModel):
    membership_id: str = Field(min_length=3, max_length=128)
    user_id: str = Field(min_length=3, max_length=128)
    role: UserRole
    organization_id: str | None = None
    patient_subject_id: str | None = None
    provider_organization_id: str | None = None
    invited_by_user_id: str | None = None

    @model_validator(mode="after")
    def validate_role_scope(self) -> "MembershipCreate":
        if self.role is UserRole.PATIENT and not self.patient_subject_id:
            raise ValueError("patient memberships require patient_subject_id")
        if self.role in {UserRole.PROVIDER, UserRole.HOSPITAL_ADMIN} and not (
            self.provider_organization_id or self.organization_id
        ):
            raise ValueError("provider/hospital memberships require an organization scope")
        return self


class ResourceGrantCreate(BaseModel):
    grant_id: str = Field(min_length=3, max_length=128)
    grantee_tenant_id: str = Field(min_length=3, max_length=64)
    resource_type: ResourceType
    resource_id: str = Field(min_length=1, max_length=160)
    permissions: frozenset[Permission] = Field(min_length=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    created_by_user_id: str = Field(min_length=3, max_length=128)

    @model_validator(mode="after")
    def validate_time_window(self) -> "ResourceGrantCreate":
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be later than starts_at")
        return self


class TenantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: str
    slug: str
    display_name: str
    tenant_type: str
    status: str
    data_region: str


class OrganizationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: str
    tenant_id: str
    parent_organization_id: str | None
    slug: str
    display_name: str
    organization_type: str
    external_identifiers: dict[str, str]
    is_active: bool


class MembershipView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    membership_id: str
    tenant_id: str
    user_id: str
    role: str
    organization_id: str | None
    status: str
    patient_subject_id: str | None
    provider_organization_id: str | None


class ResourceGrantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    grant_id: str
    owner_tenant_id: str
    grantee_tenant_id: str
    resource_type: str
    resource_id: str
    permissions: list[str]
    is_active: bool
    starts_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None


class PersistenceModelResponse(BaseModel):
    isolation_strategy: tuple[str, ...]
    persisted_entities: tuple[str, ...]
    grant_lifecycle: tuple[str, ...]
    tenant_context: str
