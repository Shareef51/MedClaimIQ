from fastapi import APIRouter

from app.schemas.tenancy import PersistenceModelResponse

router = APIRouter(prefix="/tenancy-model", tags=["tenancy-model"])


@router.get("", response_model=PersistenceModelResponse)
def get_tenancy_model() -> PersistenceModelResponse:
    """Expose architecture metadata only; no tenant data is returned."""

    return PersistenceModelResponse(
        isolation_strategy=(
            "server_resolved_tenant_context",
            "tenant_scoped_repository_predicates",
            "postgresql_row_level_security",
            "deny_by_default_authorization",
        ),
        persisted_entities=(
            "tenant",
            "organization",
            "user_account",
            "tenant_membership",
            "resource_grant",
        ),
        grant_lifecycle=("created", "scheduled", "active", "expired", "revoked"),
        tenant_context="transaction_local_postgresql_setting:app.current_tenant_id",
    )
