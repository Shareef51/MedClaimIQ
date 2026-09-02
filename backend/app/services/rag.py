from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, replace
from time import perf_counter
from datetime import UTC, datetime, timedelta
from typing import Sequence

from app.domain.rag import (
    ChunkKind, IndexAction, KnowledgeDocument, QueryPlan, RAGDomain, RetrievalAssessment,
    RetrievalHit, RetrievalScope, RetrievalStrategy,
)
from app.embeddings.batching import CachedBatchEmbedder
from app.models.rag import RAGIndexRecordModel
from app.rag.assessment import assess_retrieval
from app.rag.chunking import ParentChildChunker
from app.rag.compression import ContextualCompressor
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.query_intelligence import DeterministicQueryPlanner
from app.rag.reranking import EvidenceAwareReranker, diversify_candidates
from app.repositories.rag import RAGRepository
from app.sparse.provider import HashedBM25SparseEncoder, SparseEncoder
from app.vector.qdrant_store import QdrantVectorStore
from app.vector.store import VectorPoint, VectorStore


@dataclass(frozen=True)
class IndexingResult:
    source_id: str
    source_version: str
    domain: str
    chunks_persisted: int
    vectors_upserted: int
    collection_name: str


class RAGIndexingService:
    def __init__(
        self,
        *,
        repository: RAGRepository,
        chunker: ParentChildChunker,
        embedder: CachedBatchEmbedder,
        vector_store: VectorStore,
        embedding_model: str,
        embedding_dimensions: int,
        index_version: str,
        sparse_encoder: SparseEncoder | None = None,
    ) -> None:
        self.repository = repository
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.index_version = index_version
        self.sparse_encoder = sparse_encoder or HashedBM25SparseEncoder()

    def index_document(self, document: KnowledgeDocument, *, replace_previous_versions: bool = True) -> IndexingResult:
        chunks = self.chunker.chunk(document)
        if not chunks:
            raise ValueError("knowledge document produced no indexable chunks")
        self.repository.save_chunks(chunks)
        if replace_previous_versions:
            self.vector_store.delete_source(document.domain, tenant_id=document.tenant_id, source_id=document.source_id, source_version=None)
            self.repository.deactivate_other_source_versions(
                source_type=document.source_type,
                source_id=document.source_id,
                keep_version=document.source_version,
            )
        self.repository.deactivate_stale_index_versions(
            source_id=document.source_id,
            source_version=document.source_version,
            keep_index_version=self.index_version,
        )
        indexable = [chunk for chunk in chunks if chunk.kind is not ChunkKind.PARENT]
        texts = [chunk.text for chunk in indexable]
        vectors = self.embedder.embed(texts)
        sparse_vectors = self.sparse_encoder.encode(texts)
        collection = self.vector_store.ensure_domain(document.domain)
        points: list[VectorPoint] = []
        records: list[RAGIndexRecordModel] = []
        now = datetime.now(UTC)
        for chunk, vector, sparse_vector in zip(indexable, vectors, sparse_vectors, strict=True):
            point_id = QdrantVectorStore.point_id(chunk.chunk_id)
            payload = {
                **chunk.metadata,
                "chunk_id": chunk.chunk_id,
                "parent_chunk_id": chunk.parent_chunk_id,
                "chunk_kind": chunk.kind.value,
                "text": chunk.text,
                "citation": chunk.citation,
                "metadata": chunk.metadata,
                "active": True,
            }
            points.append(VectorPoint(point_id=point_id, vector=vector, sparse_vector=sparse_vector, payload=payload))
            records.append(
                RAGIndexRecordModel(
                    index_record_id=f"ridx_{uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id + self.embedding_model + str(self.embedding_dimensions) + self.index_version).hex}",
                    tenant_id=chunk.tenant_id,
                    claim_id=chunk.claim_id,
                    chunk_id=chunk.chunk_id,
                    domain=chunk.domain.value,
                    source_id=chunk.source_id,
                    source_version=chunk.source_version,
                    collection_name=collection,
                    point_id=point_id,
                    embedding_model=self.embedding_model,
                    embedding_dimensions=self.embedding_dimensions,
                    embedding_input_sha256=hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    index_version=self.index_version,
                    active=True,
                    indexed_at=now,
                )
            )
        self.vector_store.upsert(document.domain, points)
        self.repository.add_index_records(records)
        return IndexingResult(
            source_id=document.source_id,
            source_version=document.source_version,
            domain=document.domain.value,
            chunks_persisted=len(chunks),
            vectors_upserted=len(points),
            collection_name=collection,
        )

    def delete_source(self, *, domain: RAGDomain, tenant_id: str, source_id: str, source_version: str | None = None) -> None:
        if tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant RAG delete denied")
        self.vector_store.delete_source(domain, tenant_id=tenant_id, source_id=source_id, source_version=source_version)
        self.repository.deactivate_source(source_id=source_id, source_version=source_version)


class DenseRetrievalService:
    def __init__(self, *, embedder: CachedBatchEmbedder, vector_store: VectorStore, repository: RAGRepository) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.repository = repository

    def search(self, *, query: str, scope: RetrievalScope, limit: int = 8, hydrate_parent: bool = True) -> list[RetrievalHit]:
        if scope.tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant RAG retrieval denied")
        if not query.strip():
            raise ValueError("query cannot be empty")
        vector = self.embedder.embed([query.strip()])[0]
        domains = scope.domains or tuple(RAGDomain)
        per_domain = max(limit, 1)
        hits: list[RetrievalHit] = []
        for domain in domains:
            query_dense = getattr(self.vector_store, "query_dense", None) or getattr(self.vector_store, "query")
            raw_hits = query_dense(domain, vector=vector, scope=scope, limit=per_domain)
            hits.extend(getattr(self.repository, "filter_governed_retrieval_hits", lambda values: list(values))(raw_hits))
        hits.sort(key=lambda item: item.score, reverse=True)
        selected = hits[:limit]
        if not hydrate_parent:
            return selected
        parent_ids = [hit.parent_chunk_id for hit in selected if hit.parent_chunk_id]
        parents = self.repository.parent_chunks(parent_ids)
        hydrated: list[RetrievalHit] = []
        for hit in selected:
            parent = parents.get(hit.parent_chunk_id or "")
            if parent is None:
                hydrated.append(hit)
                continue
            metadata = dict(hit.metadata)
            metadata["matched_child_text"] = hit.text
            hydrated.append(replace(hit, text=parent.content_text, metadata=metadata))
        return hydrated



@dataclass(frozen=True)
class HybridRetrievalResult:
    retrieval_run_id: str
    query: str
    plan: QueryPlan
    hits: tuple[RetrievalHit, ...]
    assessment: RetrievalAssessment
    fallback_steps: tuple[str, ...]
    latency_ms: int


class RetrievalTelemetrySink:
    def record(
        self,
        *,
        run_id: str,
        query: str,
        plan: QueryPlan,
        strategy: RetrievalStrategy,
        candidates: Sequence[RetrievalHit],
        selected: Sequence[RetrievalHit],
        assessment: RetrievalAssessment,
        fallback_steps: Sequence[str],
        latency_ms: int,
        compression_applied: bool,
        trace_id: str | None,
    ) -> None:
        raise NotImplementedError


class HybridRetrievalService:
    """Security-scoped hybrid retrieval with deterministic planning and evidence-aware reranking."""

    def __init__(
        self,
        *,
        embedder: CachedBatchEmbedder,
        vector_store: VectorStore,
        repository: RAGRepository,
        sparse_encoder: SparseEncoder | None = None,
        planner: DeterministicQueryPlanner | None = None,
        reranker: EvidenceAwareReranker | None = None,
        compressor: ContextualCompressor | None = None,
        telemetry: RetrievalTelemetrySink | None = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        minimum_confidence: float = 0.35,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.repository = repository
        self.sparse_encoder = sparse_encoder or HashedBM25SparseEncoder()
        self.planner = planner or DeterministicQueryPlanner()
        self.reranker = reranker or EvidenceAwareReranker()
        self.compressor = compressor or ContextualCompressor()
        self.telemetry = telemetry
        self.rrf_k = rrf_k
        self.candidate_multiplier = max(2, candidate_multiplier)
        self.minimum_confidence = minimum_confidence

    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        limit: int = 8,
        hydrate_parent: bool = True,
        compress_context: bool = True,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        trace_id: str | None = None,
        prepared_plan: QueryPlan | None = None,
        candidate_multiplier_override: int | None = None,
    ) -> HybridRetrievalResult:
        if scope.tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant RAG retrieval denied")
        if not query.strip():
            raise ValueError("query cannot be empty")
        if limit <= 0:
            raise ValueError("limit must be positive")
        started = perf_counter()
        plan = prepared_plan or self.planner.plan(
            query,
            requested_domains=scope.domains,
            service_date_from=scope.service_date_from,
            service_date_to=scope.service_date_to,
            minimum_authority_rank=scope.minimum_authority_rank,
        )
        self._validate_prepared_plan(plan, scope)
        planned_scope = replace(
            scope,
            domains=plan.domains,
            service_date_from=plan.service_date_from,
            service_date_to=plan.service_date_to,
            minimum_authority_rank=plan.minimum_authority_rank,
        )
        multiplier = self.candidate_multiplier if candidate_multiplier_override is None else max(2, min(8, int(candidate_multiplier_override)))
        candidate_limit = max(limit * multiplier, 12)
        ranked_lists = self._candidate_lists(plan, planned_scope, candidate_limit, strategy)
        fallback_steps: list[str] = []
        if not any(ranked_lists) and not scope.domains and set(plan.domains) != set(RAGDomain):
            fallback_steps.append("expanded_to_all_authorized_domains")
            expanded_scope = replace(planned_scope, domains=tuple(RAGDomain))
            ranked_lists = self._candidate_lists(plan, expanded_scope, candidate_limit, strategy)
            plan = replace(plan, domains=tuple(RAGDomain))

        fused = reciprocal_rank_fusion(ranked_lists, k=self.rrf_k) if ranked_lists else []
        reranked = self.reranker.rerank(plan.normalized_query, fused, plan=plan)
        selected = diversify_candidates(reranked, limit=limit)
        if hydrate_parent:
            selected = self._hydrate_parents(selected)
        if compress_context:
            selected = self.compressor.compress(plan.normalized_query, selected)
        assessment = assess_retrieval(selected, plan=plan, minimum_confidence=self.minimum_confidence)
        if assessment.no_evidence:
            fallback_steps.append("explicit_no_evidence")
        latency_ms = max(0, int((perf_counter() - started) * 1000))
        run_id = f"retr_{uuid.uuid4().hex}"
        if self.telemetry is not None:
            self.telemetry.record(
                run_id=run_id,
                query=query,
                plan=plan,
                strategy=strategy,
                candidates=reranked,
                selected=selected,
                assessment=assessment,
                fallback_steps=fallback_steps,
                latency_ms=latency_ms,
                compression_applied=compress_context,
                trace_id=trace_id,
            )
        return HybridRetrievalResult(
            retrieval_run_id=run_id,
            query=query,
            plan=plan,
            hits=tuple(selected),
            assessment=assessment,
            fallback_steps=tuple(fallback_steps),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _validate_prepared_plan(plan: QueryPlan, scope: RetrievalScope) -> None:
        authorized_domains = set(scope.domains or tuple(RAGDomain))
        if not set(plan.domains).issubset(authorized_domains):
            raise PermissionError("prepared retrieval plan attempted to broaden authorized domains")
        if plan.minimum_authority_rank < scope.minimum_authority_rank:
            raise PermissionError("prepared retrieval plan attempted to lower authority threshold")
        if scope.service_date_from and (plan.service_date_from is None or plan.service_date_from < scope.service_date_from):
            raise PermissionError("prepared retrieval plan attempted to broaden lower temporal bound")
        if scope.service_date_to and (plan.service_date_to is None or plan.service_date_to > scope.service_date_to):
            raise PermissionError("prepared retrieval plan attempted to broaden upper temporal bound")

    def _candidate_lists(
        self,
        plan: QueryPlan,
        scope: RetrievalScope,
        candidate_limit: int,
        strategy: RetrievalStrategy,
    ) -> list[list[RetrievalHit]]:
        query_texts = list(dict.fromkeys((*plan.variants, *plan.subqueries)))[:6]
        dense_vectors: list[list[float]] = []
        if strategy in (RetrievalStrategy.HYBRID, RetrievalStrategy.DENSE):
            dense_vectors = self.embedder.embed(query_texts)
        sparse_vectors = []
        if strategy in (RetrievalStrategy.HYBRID, RetrievalStrategy.SPARSE):
            sparse_vectors = self.sparse_encoder.encode(query_texts)
        ranked: list[list[RetrievalHit]] = []
        domains = scope.domains or tuple(RAGDomain)
        for q_index, query_text in enumerate(query_texts):
            for domain in domains:
                if dense_vectors:
                    query_dense = getattr(self.vector_store, "query_dense", None) or getattr(self.vector_store, "query")
                    hits = query_dense(domain, vector=dense_vectors[q_index], scope=scope, limit=candidate_limit)
                    hits = getattr(self.repository, "filter_governed_retrieval_hits", lambda values: list(values))(hits)
                    ranked.append([replace(hit, query_variant=query_text) for hit in hits])
                if sparse_vectors and sparse_vectors[q_index].indices:
                    query_sparse = getattr(self.vector_store, "query_sparse", None)
                    if query_sparse is not None:
                        hits = query_sparse(domain, vector=sparse_vectors[q_index], scope=scope, limit=candidate_limit)
                        hits = getattr(self.repository, "filter_governed_retrieval_hits", lambda values: list(values))(hits)
                        ranked.append([replace(hit, query_variant=query_text) for hit in hits])
        return ranked

    def _hydrate_parents(self, selected: Sequence[RetrievalHit]) -> list[RetrievalHit]:
        parent_ids = [hit.parent_chunk_id for hit in selected if hit.parent_chunk_id]
        parents = self.repository.parent_chunks(parent_ids)
        hydrated: list[RetrievalHit] = []
        for hit in selected:
            parent = parents.get(hit.parent_chunk_id or "")
            if parent is None:
                hydrated.append(hit)
                continue
            metadata = dict(hit.metadata)
            metadata["matched_child_text"] = hit.text
            metadata["parent_hydrated"] = True
            hydrated.append(replace(hit, text=parent.content_text, metadata=metadata))
        return hydrated

def retry_delay_seconds(*, attempt: int, base_seconds: int = 15, max_seconds: int = 600) -> int:
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    return min(max_seconds, base_seconds * (2 ** (attempt - 1)))


def rag_model_contract() -> dict[str, object]:
    return {
        "domains": [item.value for item in RAGDomain],
        "retrieval_foundation": [
            "hybrid dense + sparse BM25-compatible retrieval",
            "reciprocal-rank fusion across query variants and domains",
            "deterministic query planning + decomposition + metadata filters",
            "evidence-aware reranking + candidate diversification",
            "contextual compression + confidence/coverage/no-evidence assessment",
            "dense cosine retrieval",
            "tenant + claim + ACL + entity + temporal metadata filters",
            "parent-child context hydration",
            "citation-preserving results",
            "retrieval telemetry without raw query persistence by default",
        ],
        "indexing": {
            "authoritative_store": "PostgreSQL chunks/jobs/projection manifests",
            "vector_projection": "Qdrant domain collections",
            "operations": [item.value for item in IndexAction],
            "idempotency": "deterministic chunk IDs + deterministic Qdrant UUID point IDs",
            "failure_handling": "retry with exponential backoff, then persistent DLQ",
        },
        "chunking": {
            "strategy": "document-aware parent/child chunks",
            "parent_tokens": 1200,
            "child_tokens": 350,
            "overlap_tokens": 60,
            "preserves": ["page", "bbox", "timestamp", "source version", "entity relationships", "ACL tags"],
        },
        "embeddings": {
            "provider": "OpenAI adapter",
            "default_model": "text-embedding-3-large",
            "batching": True,
            "cache": "Redis-compatible content/model/dimension keyed cache",
        },
        "safety": (
            "Retrieval is deny-by-default across tenants: tenant scope is mandatory and Qdrant filtering occurs before results are returned. "
            "PostgreSQL remains authoritative; vector collections are rebuildable projections."
        ),
    }
