from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from app.domain.cross_source_rag import (
    ContradictionSummary, EvidenceItem, EvidencePack, RetrieverKind, UnifiedCitation, evidence_key,
)
from app.domain.rag import RetrievalScope, RetrievalStrategy
from app.rag.cross_source_planning import DeterministicCrossSourcePlanner
from app.rag.evidence_fusion import CrossSourceEvidenceFusion
from app.rag.fhir_retrieval import FHIRStructuredRetriever
from app.rag.graph_retrieval import BoundedGraphRAGRetriever
from app.rag.structured_retrieval import StructuredSQLRetriever
from app.repositories.cross_source_rag import CrossSourceRepository


class HybridSearchProtocol(Protocol):
    def search(self, *, query: str, scope: RetrievalScope, limit: int, hydrate_parent: bool, compress_context: bool, strategy: RetrievalStrategy, trace_id: str | None = None): ...


@dataclass(frozen=True, slots=True)
class CrossSourceSearchResult:
    pack: EvidencePack
    requested_retrievers: tuple[RetrieverKind, ...]


class CrossSourceEvidenceService:
    def __init__(
        self,
        *,
        repository: CrossSourceRepository,
        hybrid_retriever: HybridSearchProtocol | None = None,
        planner: DeterministicCrossSourcePlanner | None = None,
        fusion: CrossSourceEvidenceFusion | None = None,
    ) -> None:
        self.repository = repository
        self.hybrid_retriever = hybrid_retriever
        self.planner = planner or DeterministicCrossSourcePlanner()
        self.fusion = fusion or CrossSourceEvidenceFusion()

    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        requested_retrievers: tuple[RetrieverKind, ...] = (),
        top_k: int = 12,
        graph_max_depth: int = 2,
        trace_id: str | None = None,
    ) -> CrossSourceSearchResult:
        if scope.tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant cross-source retrieval denied")
        if not scope.claim_id:
            raise ValueError("claim-scoped retrieval requires claim_id")
        plan = self.planner.plan(
            query=query, claim_id=scope.claim_id, requested_retrievers=requested_retrievers,
            service_date_from=scope.service_date_from, service_date_to=scope.service_date_to,
            graph_max_depth=graph_max_depth,
        )
        items: list[EvidenceItem] = []
        executed: list[RetrieverKind] = []
        if RetrieverKind.SQL in plan.retrievers:
            items.extend(StructuredSQLRetriever(self.repository).retrieve(plan.structured)); executed.append(RetrieverKind.SQL)
        if RetrieverKind.FHIR in plan.retrievers:
            items.extend(FHIRStructuredRetriever(self.repository).retrieve(plan.fhir)); executed.append(RetrieverKind.FHIR)
        if RetrieverKind.GRAPH in plan.retrievers:
            items.extend(BoundedGraphRAGRetriever(self.repository).retrieve(plan.graph)); executed.append(RetrieverKind.GRAPH)
        if RetrieverKind.VECTOR in plan.retrievers and self.hybrid_retriever is not None:
            result = self.hybrid_retriever.search(
                query=query, scope=scope, limit=top_k, hydrate_parent=False, compress_context=False,
                strategy=RetrievalStrategy.HYBRID, trace_id=trace_id,
            )
            for hit in result.hits:
                metadata = dict(hit.metadata or {})
                citation_data = dict(hit.citation or {})
                items.append(EvidenceItem(
                    evidence_key=evidence_key("vector", hit.chunk_id), retriever=RetrieverKind.VECTOR,
                    source_type=str(metadata.get("source_type") or "rag_chunk"),
                    source_id=str(metadata.get("source_id") or hit.chunk_id),
                    source_version=str(metadata.get("source_version") or "") or None,
                    text=hit.text, authority_rank=int(metadata.get("authority_rank") or 0),
                    confidence=float(metadata.get("evidence_confidence") or hit.score or 0.0),
                    citation=UnifiedCitation(
                        source_type=str(metadata.get("source_type") or "rag_chunk"),
                        source_id=str(metadata.get("source_id") or hit.chunk_id),
                        source_version=str(metadata.get("source_version") or "") or None,
                        locator=citation_data,
                        entity_ids=tuple(metadata.get("entity_ids") or ()),
                        relationship_path=tuple(metadata.get("relationship_types") or ()),
                    ), metadata={**metadata, "chunk_id": hit.chunk_id, "vector_score": hit.score},
                ))
            executed.append(RetrieverKind.VECTOR)

        if scope.minimum_authority_rank > 0:
            items = [item for item in items if item.authority_rank >= scope.minimum_authority_rank]

        contradictions = tuple(
            ContradictionSummary(
                contradiction_id=row.contradiction_id, field_name=row.field_name, severity=row.severity,
                confidence=float(row.confidence), left_value=row.left_value, right_value=row.right_value,
                status=row.status,
            )
            for row in self.repository.open_contradictions(scope.claim_id)
        )
        pack = self.fusion.fuse(
            claim_id=scope.claim_id, query=query, items=tuple(items), contradictions=contradictions,
            planned_retrievers=plan.retrievers, executed_retrievers=tuple(executed),
            planner_version=plan.planner_version, limit=max(top_k, 8),
        )
        self.repository.save_evidence_pack(
            pack, query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(), query_length=len(query),
            requested_retrievers=tuple(item.value for item in plan.retrievers), trace_id=trace_id,
        )
        return CrossSourceSearchResult(pack=pack, requested_retrievers=plan.retrievers)


def cross_source_rag_model_contract() -> dict[str, object]:
    return {
        "retrievers": [item.value for item in RetrieverKind],
        "structured_query_safety": {
            "mode": "typed whitelisted SQLAlchemy query plans",
            "arbitrary_sql_generation": False,
            "tenant_and_claim_scope": "mandatory and non-relaxable",
        },
        "graph_rag": {
            "authoritative_graph": "PostgreSQL evidence graph",
            "max_depth": 4,
            "max_edges": 200,
            "arbitrary_graph_query_generation": False,
            "claim_scoped": True,
        },
        "fhir_rag": {
            "source": "versioned persisted FHIR snapshots",
            "supported_resources": ["Patient", "Encounter", "Coverage", "Claim", "ExplanationOfBenefit", "DocumentReference", "Organization", "Practitioner"],
        },
        "fusion": [
            "authority-aware evidence ordering", "provenance-preserving unified citations",
            "explicit unresolved contradiction propagation", "cross-retriever coverage/confidence scoring",
            "immutable evidence-pack snapshots for downstream agents",
        ],
        "privacy": "raw reviewer queries are hashed in persisted evidence-pack telemetry; pack items persist hashes/citations, not duplicated evidence text",
        "safety": "retrieval can support human claim review but cannot autonomously finalize a claim decision",
    }
