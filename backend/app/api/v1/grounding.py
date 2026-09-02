from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.core.config import get_settings
from app.domain.grounding import CandidateCitation, CandidateStatement
from app.domain.rag import RetrievalScope
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.repositories.cross_source_rag import CrossSourceRepository
from app.repositories.grounding import GroundingGuardrailRepository
from app.repositories.rag import RAGRepository
from app.schemas.grounding import (
    AnswerabilityResponse, EvidenceQualityResponse, GroundingCheckRequest, GroundingCheckResponse,
    InjectionFindingResponse, RepairAttemptResponse, SafeEvidenceResponse, StatementGroundingResponse,
)
from app.services.cross_source_rag import CrossSourceEvidenceService
from app.services.grounding import GroundingGuardrailService, grounding_guardrail_model_contract
from app.guardrails.answerability import AnswerabilityGate, EvidenceQualityGate
from app.guardrails.prompt_injection import RetrievedContentPromptInjectionScanner
from app.services.rag import HybridRetrievalService

router = APIRouter(tags=["rag-grounding-guardrails"])


@router.get("/rag-grounding-model")
def model_contract() -> dict[str, object]:
    return grounding_guardrail_model_contract()


@router.post("/claims/{claim_id}/rag/grounding-check", response_model=GroundingCheckResponse)
def grounding_check(
    claim_id: str,
    payload: GroundingCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GroundingCheckResponse:
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
    rag_repo = RAGRepository(db, tenant_id=identity.principal.tenant_id)
    hybrid = HybridRetrievalService(
        embedder=request.app.state.rag_embedder_provider(),
        vector_store=request.app.state.rag_vector_store_provider(),
        repository=rag_repo,
        telemetry=PostgresRetrievalTelemetry(rag_repo),
    )
    cross_source = CrossSourceEvidenceService(
        repository=CrossSourceRepository(db, identity.principal.tenant_id), hybrid_retriever=hybrid,
    )
    settings = get_settings()
    guardrails = GroundingGuardrailService(
        cross_source=cross_source,
        repository=GroundingGuardrailRepository(db, identity.principal.tenant_id),
        injection_scanner=RetrievedContentPromptInjectionScanner(
            suspicious_threshold=settings.rag_prompt_injection_suspicious_threshold,
            block_threshold=settings.rag_prompt_injection_block_threshold,
        ),
        quality_gate=EvidenceQualityGate(
            minimum_item_confidence=settings.rag_guardrail_minimum_item_confidence,
            minimum_authority_rank=settings.rag_guardrail_minimum_authority_rank,
            minimum_quality_score=settings.rag_guardrail_minimum_quality_score,
        ),
        answerability_gate=AnswerabilityGate(
            minimum_quality_score=settings.rag_guardrail_minimum_quality_score,
            minimum_pack_coverage=settings.rag_guardrail_minimum_pack_coverage,
        ),
    )
    statements = tuple(
        CandidateStatement(
            statement_id=item.statement_id,
            text=item.text,
            citations=tuple(CandidateCitation(
                evidence_key=citation.evidence_key, source_id=citation.source_id,
                source_version=citation.source_version, locator=citation.locator,
            ) for citation in item.citations),
        )
        for item in payload.candidate_statements
    )
    result = guardrails.run(
        query=payload.query, scope=scope, candidate_statements=statements,
        requested_retrievers=payload.retrievers, top_k=payload.top_k,
        graph_max_depth=payload.graph_max_depth, max_repairs=min(payload.max_repairs, settings.rag_guardrail_max_repairs),
        trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
    )
    grounding = result.grounding
    return GroundingCheckResponse(
        run_id=grounding.run_id, claim_id=claim_id, pack_id=grounding.pack.pack_id,
        decision=grounding.decision, guardrail_version=grounding.guardrail_version,
        evidence_quality=EvidenceQualityResponse(
            score=grounding.evidence_quality.score,
            qualifying_evidence_count=grounding.evidence_quality.qualifying_evidence_count,
            authoritative_evidence_count=grounding.evidence_quality.authoritative_evidence_count,
            source_type_count=grounding.evidence_quality.source_type_count,
            excluded_injection_count=grounding.evidence_quality.excluded_injection_count,
            unresolved_material_contradictions=grounding.evidence_quality.unresolved_material_contradictions,
            reasons=list(grounding.evidence_quality.reasons),
        ),
        answerability=AnswerabilityResponse(
            answerable=grounding.answerability.answerable, score=grounding.answerability.score,
            reasons=list(grounding.answerability.reasons), requires_repair=grounding.answerability.requires_repair,
            requires_human_review=grounding.answerability.requires_human_review,
        ),
        injection_findings=[InjectionFindingResponse(
            evidence_key=item.evidence_key, risk=item.risk, score=item.score,
            rule_ids=list(item.rule_ids), action=item.action,
        ) for item in grounding.screened.findings],
        safe_evidence=[SafeEvidenceResponse(
            evidence_key=item.evidence_key, source_type=item.source_type, source_id=item.source_id,
            source_version=item.source_version, text=item.text, authority_rank=item.authority_rank,
            confidence=item.confidence,
            citation={
                "source_type": item.citation.source_type, "source_id": item.citation.source_id,
                "source_version": item.citation.source_version, "locator": item.citation.locator,
                "entity_ids": list(item.citation.entity_ids), "relationship_path": list(item.citation.relationship_path),
            },
        ) for item in grounding.screened.safe_items],
        statement_checks=[StatementGroundingResponse(
            statement_id=item.statement_id, support=item.support, support_score=item.support_score,
            citation_status=item.citation.status,
            verified_evidence_keys=list(item.citation.verified_evidence_keys),
            invalid_evidence_keys=list(item.citation.invalid_evidence_keys),
            numeric_integrity=item.numeric_integrity, medical_code_integrity=item.medical_code_integrity,
            contradiction_safe=item.contradiction_safe, reasons=list(item.reasons),
        ) for item in grounding.statement_checks],
        repair_attempts=[RepairAttemptResponse(
            attempt_number=item.attempt_number, strategy=item.strategy,
            requested_retrievers=list(item.requested_retrievers), result_pack_id=item.result_pack_id,
            confidence=item.confidence, answerable=item.answerable,
        ) for item in grounding.repairs],
        escalation_reasons=list(grounding.escalation_reasons),
        generation_contract={
            "system_rules": list(result.prompt_envelope.system_rules),
            "required_output_contract": result.prompt_envelope.required_output_contract,
            "safe_evidence_count": len(result.prompt_envelope.evidence_blocks),
            "contradiction_count": len(result.prompt_envelope.contradiction_blocks),
        },
    )
