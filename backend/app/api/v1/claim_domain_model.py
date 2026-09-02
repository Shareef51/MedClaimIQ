from fastapi import APIRouter

from app.schemas.claims import ClaimDomainModelResponse

router = APIRouter(prefix="/claim-domain-model", tags=["claim-domain-model"])


@router.get("", response_model=ClaimDomainModelResponse)
def get_claim_domain_model() -> ClaimDomainModelResponse:
    """Expose architecture metadata only; no medical claim or patient data is returned."""

    return ClaimDomainModelResponse(
        persisted_entities=(
            "patient",
            "provider",
            "policy",
            "encounter",
            "claim",
            "claim_line",
            "evidence_artifact",
            "evidence_lineage",
            "claim_status_event",
            "human_review_decision",
            "audit_event",
        ),
        lifecycle_controls=(
            "canonical_transition_graph",
            "row_lock_for_mutating_transition",
            "optimistic_status_version",
            "tenant_scoped_idempotency_key",
            "human_finalization_boundary",
        ),
        provenance_controls=(
            "content_sha256",
            "source_system_and_locator",
            "immutable_evidence_lineage",
            "immutable_status_history",
            "immutable_human_decision",
            "immutable_audit_event",
        ),
        database_isolation=(
            "explicit_tenant_repository_predicates",
            "transaction_local_postgresql_tenant_context",
            "postgresql_row_level_security",
            "forced_row_level_security",
        ),
        final_decision_boundary=(
            "Only a persisted authorized human-review decision may drive a claim from "
            "human_review to a final completed state."
        ),
    )
