from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType
from app.domain.rag import RetrievalScope
from app.repositories.claims import ClaimRepository
from app.repositories.rag import RAGRepository
from app.schemas.rag import (
    DenseSearchHit, DenseSearchRequest, DenseSearchResponse, HybridSearchHit, HybridSearchRequest,
    HybridSearchResponse, QueryPlanResponse, RetrievalAssessmentResponse,
)
from app.security.authentication import RequestIdentity
from app.services.authorization import authorization_service
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.services.rag import DenseRetrievalService, HybridRetrievalService, rag_model_contract

router = APIRouter(tags=["rag"])


def _identity(request: Request) -> RequestIdentity:
    identity: RequestIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    return identity


def _authorize_claim_read(db: Session, identity: RequestIdentity, claim_id: str):
    claim = ClaimRepository(db, identity.principal.tenant_id).get(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim was not found")
    resource = ResourceAccessContext(
        resource_type=ResourceType.CLAIM,
        resource_id=claim.claim_id,
        owner_tenant_id=claim.tenant_id,
        owner_patient_subject_id=claim.patient_subject_id,
        related_provider_organization_id=claim.provider_organization_id,
        assigned_reviewer_user_id=claim.assigned_reviewer_user_id,
    )
    decision = authorization_service.evaluate(
        AccessRequest(principal=identity.principal, permission=Permission.CLAIM_READ, resource=resource)
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="access to the claim resource is denied")
    return claim


@router.get("/rag-model")
def rag_model() -> dict[str, object]:
    return rag_model_contract()


@router.post("/claims/{claim_id}/rag/search", response_model=DenseSearchResponse)
def dense_claim_search(
    claim_id: str,
    payload: DenseSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> DenseSearchResponse:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    # ACL tags are derived from the persisted principal and successful claim authorization.
    # They are never accepted from the client request body or JWT role/tenant claims.
    acl_tags = (
        "claim_authorized",
        f"role:{identity.principal.role.value}",
        f"user:{identity.principal.user_id}",
    )
    scope = RetrievalScope(
        tenant_id=identity.principal.tenant_id,
        claim_id=claim.claim_id,
        patient_subject_id=claim.patient_subject_id,
        domains=payload.domains,
        acl_tags=acl_tags,
        entity_ids=payload.entity_ids,
    )
    service = DenseRetrievalService(
        embedder=request.app.state.rag_embedder_provider(),
        vector_store=request.app.state.rag_vector_store_provider(),
        repository=RAGRepository(db, tenant_id=identity.principal.tenant_id),
    )
    hits = service.search(
        query=payload.query,
        scope=scope,
        limit=payload.top_k,
        hydrate_parent=payload.hydrate_parent,
    )
    return DenseSearchResponse(
        claim_id=claim_id,
        query=payload.query,
        hits=[
            DenseSearchHit(
                chunk_id=hit.chunk_id,
                domain=hit.domain,
                score=hit.score,
                text=hit.text,
                parent_chunk_id=hit.parent_chunk_id,
                citation=hit.citation,
                metadata=hit.metadata,
            )
            for hit in hits
        ],
    )


@router.post("/claims/{claim_id}/rag/hybrid-search", response_model=HybridSearchResponse)
def hybrid_claim_search(
    claim_id: str,
    payload: HybridSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> HybridSearchResponse:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    acl_tags = (
        "claim_authorized",
        f"role:{identity.principal.role.value}",
        f"user:{identity.principal.user_id}",
    )
    service_from = payload.service_date_from
    service_to = payload.service_date_to
    if service_from and service_to and service_to < service_from:
        raise HTTPException(status_code=422, detail="service_date_to must be on or after service_date_from")
    scope = RetrievalScope(
        tenant_id=identity.principal.tenant_id,
        claim_id=claim.claim_id,
        patient_subject_id=claim.patient_subject_id,
        domains=payload.domains,
        acl_tags=acl_tags,
        entity_ids=payload.entity_ids,
        service_date_from=service_from,
        service_date_to=service_to,
        minimum_authority_rank=payload.minimum_authority_rank,
    )
    repository = RAGRepository(db, tenant_id=identity.principal.tenant_id)
    service = HybridRetrievalService(
        embedder=request.app.state.rag_embedder_provider(),
        vector_store=request.app.state.rag_vector_store_provider(),
        repository=repository,
        telemetry=PostgresRetrievalTelemetry(repository),
    )
    result = service.search(
        query=payload.query,
        scope=scope,
        limit=payload.top_k,
        hydrate_parent=payload.hydrate_parent,
        compress_context=payload.compress_context,
        strategy=payload.strategy,
        trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
    )
    return HybridSearchResponse(
        claim_id=claim_id,
        retrieval_run_id=result.retrieval_run_id,
        query=result.query,
        strategy=payload.strategy,
        plan=QueryPlanResponse(
            normalized_query=result.plan.normalized_query,
            variants=list(result.plan.variants),
            subqueries=list(result.plan.subqueries),
            domains=list(result.plan.domains),
            exact_terms=list(result.plan.exact_terms),
            service_date_from=result.plan.service_date_from,
            service_date_to=result.plan.service_date_to,
            minimum_authority_rank=result.plan.minimum_authority_rank,
            planner_version=result.plan.planner_version,
            fallbacks=list(result.plan.fallbacks),
        ),
        assessment=RetrievalAssessmentResponse(
            confidence=result.assessment.confidence,
            coverage=result.assessment.coverage,
            source_diversity=result.assessment.source_diversity,
            no_evidence=result.assessment.no_evidence,
            reasons=list(result.assessment.reasons),
        ),
        fallback_steps=list(result.fallback_steps),
        latency_ms=result.latency_ms,
        hits=[
            HybridSearchHit(
                chunk_id=hit.chunk_id,
                domain=hit.domain,
                score=hit.score,
                dense_score=hit.dense_score,
                sparse_score=hit.sparse_score,
                fused_score=hit.fused_score,
                rerank_score=hit.rerank_score,
                text=hit.text,
                parent_chunk_id=hit.parent_chunk_id,
                citation=hit.citation,
                metadata=hit.metadata,
                retrieval_sources=list(hit.retrieval_sources),
            )
            for hit in result.hits
        ],
    )
