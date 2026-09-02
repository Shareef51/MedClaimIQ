from fastapi import APIRouter

from app.domain.access import ROLE_DESCRIPTIONS, ROLE_PERMISSIONS, TenantType, UserRole
from app.schemas.access import AccessModelResponse, RoleDefinition

router = APIRouter(prefix="/access-model", tags=["access-model"])


@router.get("", response_model=AccessModelResponse)
def get_access_model() -> AccessModelResponse:
    """Expose non-sensitive role metadata for documentation/UI capability rendering.

    This endpoint does not authorize requests. Server-side authorization must always
    evaluate the authenticated principal against the requested resource.
    """

    roles = tuple(
        RoleDefinition(
            role=role,
            description=ROLE_DESCRIPTIONS[role],
            permissions=tuple(sorted(ROLE_PERMISSIONS[role], key=str)),
        )
        for role in UserRole
    )
    return AccessModelResponse(
        policy_id="medclaimiq.authz.v1",
        default_effect="deny",
        tenant_types=tuple(TenantType),
        principles=(
            "least_privilege",
            "tenant_isolation",
            "explicit_cross_tenant_grants",
            "server_resolved_attributes",
            "separation_of_duties",
            "human_final_claim_decision",
        ),
        roles=roles,
    )
