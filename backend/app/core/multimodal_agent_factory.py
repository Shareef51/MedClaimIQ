from __future__ import annotations

from app.domain.rag import RetrievalScope
from app.rag.knowledge_gap import KnowledgeGapDetector
from app.rag.telemetry import PostgresRetrievalTelemetry
from app.repositories.advanced_rag import AdvancedRAGRepository
from app.repositories.multimodal_rag import MultimodalRAGRepository
from app.repositories.rag import RAGRepository
from app.services.advanced_rag import AdvancedAgenticRAGService
from app.services.multimodal_agent_orchestration import MultimodalAgentInvestigationService
from app.services.multimodal_rag import MultimodalRAGService
from app.services.rag import HybridRetrievalService


def build_multimodal_agent_investigation_service(*, session, tenant_id: str, settings, embedder, vector_store):
    rag_repo=RAGRepository(session,tenant_id=tenant_id)
    text=AdvancedAgenticRAGService(
        base_retriever=HybridRetrievalService(
            embedder=embedder, vector_store=vector_store, repository=rag_repo,
            telemetry=PostgresRetrievalTelemetry(rag_repo), rrf_k=settings.rag_rrf_k,
            candidate_multiplier=settings.rag_candidate_multiplier,
            minimum_confidence=settings.rag_minimum_retrieval_confidence,
        ),
        repository=AdvancedRAGRepository(session,tenant_id=tenant_id),
        gap_detector=KnowledgeGapDetector(
            minimum_confidence=settings.rag_advanced_gap_confidence,
            minimum_citation_coverage=settings.rag_advanced_min_citation_coverage,
        ),
        max_rounds=settings.rag_advanced_max_rounds,
    )
    mm=MultimodalRAGService(
        repository=MultimodalRAGRepository(session,tenant_id=tenant_id),
        text_retriever=text,max_candidates=settings.rag_multimodal_max_candidates,
    )
    return MultimodalAgentInvestigationService(session=session,tenant_id=tenant_id,retrieval_service=mm)
