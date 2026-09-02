from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType
from app.domain.rag import RetrievalScope
from app.rag.knowledge_gap import KnowledgeGapDetector
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.repositories.advanced_rag import AdvancedRAGRepository
from app.repositories.claims import ClaimRepository
from app.repositories.multimodal_rag import MultimodalRAGRepository
from app.repositories.rag import RAGRepository
from app.schemas.multimodal_rag import (
    MultimodalCitationResponse, MultimodalGapResponse, MultimodalInconsistencyResponse, MultimodalItemResponse,
    MultimodalPlanResponse, MultimodalRAGRequest, MultimodalRAGResponse, MultimodalRunSummary,
)
from app.security.authentication import RequestIdentity
from app.services.advanced_rag import AdvancedAgenticRAGService
from app.services.authorization import authorization_service
from app.services.multimodal_rag import MultimodalRAGService
from app.services.rag import HybridRetrievalService
from app.domain.multimodal_rag import multimodal_model_contract

router = APIRouter(tags=["multimodal-rag"])
settings = get_settings()


def _identity(request: Request) -> RequestIdentity:
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    return identity


def _scope(db: Session, identity: RequestIdentity, claim_id: str, payload: MultimodalRAGRequest) -> RetrievalScope:
    claim = ClaimRepository(db, identity.principal.tenant_id).get(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim was not found")
    resource = ResourceAccessContext(
        resource_type=ResourceType.CLAIM, resource_id=claim.claim_id, owner_tenant_id=claim.tenant_id,
        owner_patient_subject_id=claim.patient_subject_id, related_provider_organization_id=claim.provider_organization_id,
        assigned_reviewer_user_id=claim.assigned_reviewer_user_id,
    )
    for permission in (Permission.CLAIM_READ, Permission.CLAIM_VIEW_AI_FINDINGS):
        if not authorization_service.evaluate(AccessRequest(identity.principal, permission, resource)).allowed:
            raise HTTPException(status_code=403, detail="multimodal RAG is restricted to authorized internal AI-review roles")
    return RetrievalScope(
        tenant_id=identity.principal.tenant_id, claim_id=claim.claim_id, patient_subject_id=claim.patient_subject_id,
        domains=payload.domains, acl_tags=("claim_authorized", f"role:{identity.principal.role.value}", f"user:{identity.principal.user_id}"),
        minimum_authority_rank=payload.minimum_authority_rank,
    )


def _service(request: Request, db: Session, identity: RequestIdentity) -> MultimodalRAGService:
    rag_repo = RAGRepository(db, tenant_id=identity.principal.tenant_id)
    text = AdvancedAgenticRAGService(
        retriever=HybridRetrievalService(
            embedder=request.app.state.rag_embedder_provider(), vector_store=request.app.state.rag_vector_store_provider(),
            repository=rag_repo, telemetry=PostgresRetrievalTelemetry(rag_repo), rrf_k=settings.rag_rrf_k,
            candidate_multiplier=settings.rag_candidate_multiplier, minimum_confidence=settings.rag_minimum_retrieval_confidence,
        ),
        repository=AdvancedRAGRepository(db, tenant_id=identity.principal.tenant_id),
        gap_detector=KnowledgeGapDetector(
            minimum_confidence=settings.rag_advanced_gap_confidence,
            minimum_citation_coverage=settings.rag_advanced_min_citation_coverage,
        ),
        max_rounds=settings.rag_advanced_max_rounds,
    )
    return MultimodalRAGService(
        repository=MultimodalRAGRepository(db, tenant_id=identity.principal.tenant_id),
        text_retriever=text,
        max_candidates=settings.rag_multimodal_max_candidates,
    )


def _plan(query, route):
    return MultimodalPlanResponse(query=query, intent=route.intent, modalities=list(route.modalities), required_modalities=list(route.required_modalities), agent=route.agent, reasons=list(route.reasons), planner_version=route.planner_version)


@router.get("/multimodal-rag-model")
def model_contract() -> dict[str, object]:
    return multimodal_model_contract()


@router.post("/claims/{claim_id}/rag/multimodal-plan", response_model=MultimodalPlanResponse)
def multimodal_plan(claim_id: str, payload: MultimodalRAGRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    _scope(db, identity, claim_id, payload)
    service = MultimodalRAGService(repository=MultimodalRAGRepository(db, tenant_id=identity.principal.tenant_id))
    route = service.plan_only(query=payload.query, requested_modalities=payload.modalities, required_modalities=payload.required_modalities, agent=payload.agent)
    return _plan(payload.query, route)


@router.post("/claims/{claim_id}/rag/multimodal-search", response_model=MultimodalRAGResponse)
def multimodal_search(claim_id: str, payload: MultimodalRAGRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    scope = _scope(db, identity, claim_id, payload)
    result = _service(request, db, identity).search(
        query=payload.query, scope=scope, agent=payload.agent, requested_modalities=payload.modalities,
        required_modalities=payload.required_modalities, limit=payload.top_k, trace_id=getattr(request.state, "trace_id", None),
    )
    db.commit()
    pack=result.pack
    return MultimodalRAGResponse(
        claim_id=claim_id, run_id=result.run_id, pack_id=pack.pack_id, plan=_plan(payload.query, result.route),
        answerability=pack.answerability, confidence=pack.confidence, modality_coverage=pack.modality_coverage,
        citation_coverage=pack.citation_coverage, source_diversity=pack.source_diversity, latency_ms=result.latency_ms,
        items=[MultimodalItemResponse(
            item_id=x.item_id, modality=x.modality, domain=x.domain, source_id=x.source_id, source_version=x.source_version,
            text=x.text, score=x.score, confidence=x.confidence, authority_rank=x.authority_rank,
            citation=MultimodalCitationResponse(**x.citation.as_dict()), metadata=x.metadata, retrieval_sources=list(x.retrieval_sources),
        ) for x in pack.items],
        inconsistencies=[MultimodalInconsistencyResponse(**{
            "code":x.code,"field":x.field,"severity":x.severity,"left_item_id":x.left_item_id,"right_item_id":x.right_item_id,
            "left_value":x.left_value,"right_value":x.right_value,"confidence":x.confidence,"description":x.description,
        }) for x in pack.inconsistencies],
        gaps=[MultimodalGapResponse(code=x.code, description=x.description, blocking=x.blocking, modality=x.modality) for x in pack.gaps],
        diagnostics=pack.diagnostics,
    )


@router.get("/claims/{claim_id}/rag/multimodal-runs", response_model=list[MultimodalRunSummary])
def multimodal_runs(claim_id: str, request: Request, limit: int = 20, db: Session = Depends(get_db)):
    identity = _identity(request)
    _scope(db, identity, claim_id, MultimodalRAGRequest(query="history"))
    rows = MultimodalRAGRepository(db, tenant_id=identity.principal.tenant_id).recent_runs(claim_id=claim_id, limit=limit)
    return [MultimodalRunSummary(
        run_id=x.run_id, intent=x.intent, routed_modalities=x.routed_modalities, selected_count=x.selected_count,
        confidence=x.confidence, modality_coverage=x.modality_coverage, citation_coverage=x.citation_coverage,
        inconsistency_count=x.inconsistency_count, answerability=x.answerability, latency_ms=x.latency_ms, created_at=x.created_at,
    ) for x in rows]
