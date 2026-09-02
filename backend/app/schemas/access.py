from pydantic import BaseModel, ConfigDict

from app.domain.access import Permission, TenantType, UserRole


class RoleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole
    description: str
    permissions: tuple[Permission, ...]


class AccessModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    default_effect: str
    tenant_types: tuple[TenantType, ...]
    principles: tuple[str, ...]
    roles: tuple[RoleDefinition, ...]
