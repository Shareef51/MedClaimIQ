from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.rag import RetrievalScope
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.repositories.cross_source_rag import CrossSourceRepository
from app.repositories.rag import RAGRepository
from app.schemas.cross_source_rag import (
    ContradictionResponse, EvidenceItemResponse, EvidencePackAssessmentResponse, EvidencePackResponse,
    EvidenceSearchRequest, UnifiedCitationResponse,
)
from app.services.cross_source_rag import CrossSourceEvidenceService, cross_source_rag_model_contract
from app.services.rag import HybridRetrievalService

router = APIRouter(tags=["cross-source-rag"])


@router.get("/cross-source-rag-model")
def model_contract() -> dict[str, object]:
    return cross_source_rag_model_contract()


@router.post("/claims/{claim_id}/rag/evidence-search", response_model=EvidencePackResponse)
def cross_source_evidence_search(
    claim_id: str,
    payload: EvidenceSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> EvidencePackResponse:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    if payload.service_date_from and payload.service_date_to and payload.service_date_to < payload.service_date_from:
        raise HTTPException(status_code=422, detail="service_date_to must be on or after service_date_from")
    acl_tags = (
        "claim_authorized", f"role:{identity.principal.role.value}", f"user:{identity.principal.user_id}",
    )
    scope = RetrievalScope(
        tenant_id=identity.principal.tenant_id, claim_id=claim.claim_id,
        patient_subject_id=claim.patient_subject_id, domains=payload.domains, acl_tags=acl_tags,
        entity_ids=payload.entity_ids, service_date_from=payload.service_date_from,
        service_date_to=payload.service_date_to, minimum_authority_rank=payload.minimum_authority_rank,
    )
    rag_repository = RAGRepository(db, tenant_id=identity.principal.tenant_id)
    hybrid = HybridRetrievalService(
        embedder=request.app.state.rag_embedder_provider(),
        vector_store=request.app.state.rag_vector_store_provider(), repository=rag_repository,
        telemetry=PostgresRetrievalTelemetry(rag_repository),
    )
    service = CrossSourceEvidenceService(
        repository=CrossSourceRepository(db, identity.principal.tenant_id), hybrid_retriever=hybrid,
    )
    result = service.search(
        query=payload.query, scope=scope, requested_retrievers=payload.retrievers,
        top_k=payload.top_k, graph_max_depth=payload.graph_max_depth,
        trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
    )
    pack = result.pack
    return EvidencePackResponse(
        claim_id=claim_id, pack_id=pack.pack_id, query=pack.query,
        requested_retrievers=list(result.requested_retrievers), executed_retrievers=list(pack.executed_retrievers),
        planner_version=pack.planner_version,
        assessment=EvidencePackAssessmentResponse(
            confidence=pack.assessment.confidence, coverage=pack.assessment.coverage,
            source_diversity=pack.assessment.source_diversity, no_evidence=pack.assessment.no_evidence,
            unresolved_material_contradictions=pack.assessment.unresolved_material_contradictions,
            reasons=list(pack.assessment.reasons),
        ),
        evidence=[EvidenceItemResponse(
            evidence_key=item.evidence_key, retriever=item.retriever, source_type=item.source_type,
            source_id=item.source_id, source_version=item.source_version, text=item.text,
            authority_rank=item.authority_rank, confidence=item.confidence,
            citation=UnifiedCitationResponse(
                source_type=item.citation.source_type, source_id=item.citation.source_id,
                source_version=item.citation.source_version, locator=item.citation.locator,
                entity_ids=list(item.citation.entity_ids), relationship_path=list(item.citation.relationship_path),
            ), metadata=item.metadata,
        ) for item in pack.items],
        contradictions=[ContradictionResponse(
            contradiction_id=item.contradiction_id, field_name=item.field_name, severity=item.severity,
            confidence=item.confidence, left_value=item.left_value, right_value=item.right_value, status=item.status,
        ) for item in pack.contradictions],
    )
