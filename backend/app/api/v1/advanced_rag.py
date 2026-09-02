from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.agents.model_client import OpenAIResponsesStructuredClient
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType
from app.domain.rag import RetrievalScope
from app.rag.advanced_query import AdvancedQueryPlanner, StructuredModelQueryTransformer
from app.rag.knowledge_gap import KnowledgeGapDetector
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.repositories.advanced_rag import AdvancedRAGRepository
from app.repositories.claims import ClaimRepository
from app.repositories.rag import RAGRepository
from app.schemas.advanced_rag import (
    AdvancedPlanResponse,
    AdvancedRAGHitResponse,
    AdvancedRAGRequest,
    AdvancedRAGResponse,
    AdvancedRAGRunSummary,
    CitationCheckResponse,
    KnowledgeGapResponse,
    MetadataPredicateResponse,
)
from app.security.authentication import RequestIdentity
from app.services.advanced_rag import AdvancedAgenticRAGService, advanced_rag_model_contract
from app.services.authorization import authorization_service
from app.services.rag import HybridRetrievalService

router = APIRouter(tags=["advanced-rag"])
settings = get_settings()


def _identity(request: Request) -> RequestIdentity:
    identity: RequestIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="authenticated identity is unavailable")
    return identity


def _claim_scope(db: Session, identity: RequestIdentity, claim_id: str, payload: AdvancedRAGRequest) -> RetrievalScope:
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
    decision = authorization_service.evaluate(AccessRequest(identity.principal, Permission.CLAIM_READ, resource))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="access to the claim resource is denied")
    ai_decision = authorization_service.evaluate(AccessRequest(identity.principal, Permission.CLAIM_VIEW_AI_FINDINGS, resource))
    if not ai_decision.allowed:
        raise HTTPException(status_code=403, detail="advanced RAG is restricted to authorized internal AI-review roles")
    if payload.service_date_from and payload.service_date_to and payload.service_date_to < payload.service_date_from:
        raise HTTPException(status_code=422, detail="service_date_to must be on or after service_date_from")
    acl_tags = ("claim_authorized", f"role:{identity.principal.role.value}", f"user:{identity.principal.user_id}")
    return RetrievalScope(
        tenant_id=identity.principal.tenant_id,
        claim_id=claim.claim_id,
        patient_subject_id=claim.patient_subject_id,
        domains=payload.domains,
        acl_tags=acl_tags,
        entity_ids=payload.entity_ids,
        source_types=payload.source_types,
        service_date_from=payload.service_date_from,
        service_date_to=payload.service_date_to,
        minimum_authority_rank=payload.minimum_authority_rank,
    )


def _service(request: Request, db: Session, identity: RequestIdentity, payload: AdvancedRAGRequest) -> AdvancedAgenticRAGService:
    rag_repo = RAGRepository(db, tenant_id=identity.principal.tenant_id)
    transformer = None
    if payload.enable_model_assisted_rewriting:
        if not settings.rag_advanced_model_assisted_rewriting_enabled:
            raise HTTPException(status_code=409, detail="model-assisted advanced RAG rewriting is disabled by server policy")
        transformer = StructuredModelQueryTransformer(OpenAIResponsesStructuredClient(), model=settings.rag_advanced_query_model)
    planner = AdvancedQueryPlanner(transformer=transformer, max_rewrites=settings.rag_advanced_max_rewrites)
    retriever = HybridRetrievalService(
        embedder=request.app.state.rag_embedder_provider(),
        vector_store=request.app.state.rag_vector_store_provider(),
        repository=rag_repo,
        telemetry=PostgresRetrievalTelemetry(rag_repo),
        rrf_k=settings.rag_rrf_k,
        candidate_multiplier=settings.rag_candidate_multiplier,
        minimum_confidence=settings.rag_minimum_retrieval_confidence,
    )
    return AdvancedAgenticRAGService(
        retriever=retriever,
        repository=AdvancedRAGRepository(db, tenant_id=identity.principal.tenant_id),
        planner=planner,
        gap_detector=KnowledgeGapDetector(
            minimum_confidence=settings.rag_advanced_gap_confidence,
            minimum_citation_coverage=settings.rag_advanced_min_citation_coverage,
        ),
        max_rounds=settings.rag_advanced_max_rounds,
    )


def _plan_response(query: str, plan) -> AdvancedPlanResponse:
    return AdvancedPlanResponse(
        query=query,
        intent=plan.intent,
        normalized_query=plan.query_plan.normalized_query,
        rewrites=list(plan.rewrites),
        hypothetical_document=plan.hypothetical_document,
        metadata_predicates=[MetadataPredicateResponse(field=p.field, operator=p.operator.value, value=p.value, source=p.source) for p in plan.metadata_predicates],
        routing_mode=plan.route.mode,
        strategy=plan.route.strategy,
        use_hyde=plan.route.use_hyde,
        planned_domains=list(plan.query_plan.domains),
        minimum_authority_rank=plan.query_plan.minimum_authority_rank,
        service_date_from=plan.query_plan.service_date_from,
        service_date_to=plan.query_plan.service_date_to,
        agent=plan.agent_directive.agent,
        required_evidence_types=list(plan.agent_directive.required_evidence_types),
        max_rounds=plan.agent_directive.max_rounds,
        planner_version=plan.planner_version,
        model_assisted=plan.model_assisted,
    )


@router.get("/advanced-rag-model")
def model_contract() -> dict[str, object]:
    return advanced_rag_model_contract()


@router.post("/claims/{claim_id}/rag/advanced-plan", response_model=AdvancedPlanResponse)
def advanced_plan(claim_id: str, payload: AdvancedRAGRequest, request: Request, db: Session = Depends(get_db)) -> AdvancedPlanResponse:
    identity = _identity(request)
    scope = _claim_scope(db, identity, claim_id, payload)
    svc = _service(request, db, identity, payload)
    plan = svc.plan_only(query=payload.query, scope=scope, agent=payload.agent, enable_hyde=payload.enable_hyde)
    return _plan_response(payload.query, plan)


@router.post("/claims/{claim_id}/rag/advanced-search", response_model=AdvancedRAGResponse)
def advanced_search(claim_id: str, payload: AdvancedRAGRequest, request: Request, db: Session = Depends(get_db)) -> AdvancedRAGResponse:
    identity = _identity(request)
    scope = _claim_scope(db, identity, claim_id, payload)
    svc = _service(request, db, identity, payload)
    result = svc.search(
        query=payload.query,
        scope=scope,
        agent=payload.agent,
        limit=payload.top_k,
        enable_hyde=payload.enable_hyde,
        strict_citations=payload.strict_citations,
        trace_id=getattr(request.state, "trace_id", None),
    )
    db.commit()
    return AdvancedRAGResponse(
        claim_id=claim_id,
        advanced_run_id=result.advanced_run_id,
        retrieval_run_id=result.retrieval_run_id,
        plan=_plan_response(payload.query, result.plan),
        answerability=result.answerability,
        confidence=result.assessment.confidence,
        coverage=result.assessment.coverage,
        source_diversity=result.assessment.source_diversity,
        citation_coverage=result.citation_coverage,
        rounds_executed=result.rounds_executed,
        latency_ms=result.latency_ms,
        fallback_steps=list(result.fallback_steps),
        knowledge_gaps=[KnowledgeGapResponse(code=g.code, severity=g.severity, description=g.description, domain=g.domain, recommended_action=g.recommended_action) for g in result.knowledge_gaps],
        citation_checks=[CitationCheckResponse(chunk_id=c.chunk_id, valid=c.valid, reasons=list(c.reasons), source_id=c.source_id, source_version=c.source_version) for c in result.citations],
        hits=[AdvancedRAGHitResponse(chunk_id=h.chunk_id, domain=h.domain, score=h.score, rerank_score=h.rerank_score, text=h.text, citation=h.citation, metadata=h.metadata, retrieval_sources=list(h.retrieval_sources)) for h in result.hits],
    )


@router.get("/claims/{claim_id}/rag/advanced-runs", response_model=list[AdvancedRAGRunSummary])
def advanced_runs(claim_id: str, request: Request, limit: int = 20, db: Session = Depends(get_db)) -> list[AdvancedRAGRunSummary]:
    identity = _identity(request)
    dummy = AdvancedRAGRequest(query="history")
    _claim_scope(db, identity, claim_id, dummy)
    rows = AdvancedRAGRepository(db, tenant_id=identity.principal.tenant_id).recent_runs(claim_id=claim_id, limit=limit)
    return [AdvancedRAGRunSummary(
        advanced_run_id=x.advanced_run_id, retrieval_run_id=x.retrieval_run_id, agent_name=x.agent_name,
        query_intent=x.query_intent, routing_mode=x.routing_mode, retrieval_strategy=x.retrieval_strategy,
        confidence=x.confidence, citation_coverage=x.citation_coverage, answerability=x.answerability,
        knowledge_gap_count=x.knowledge_gap_count, latency_ms=x.latency_ms, created_at=x.created_at,
    ) for x in rows]
