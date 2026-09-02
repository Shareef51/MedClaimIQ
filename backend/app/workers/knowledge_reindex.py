from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4, uuid5, NAMESPACE_URL

from app.domain.knowledge_governance import ReindexAction, ReindexStatus
from app.domain.rag import RAGDomain
from app.models.rag import RAGIndexRecordModel
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository
from app.repositories.rag import RAGRepository
from app.sparse.provider import HashedBM25SparseEncoder
from app.vector.qdrant_store import QdrantVectorStore
from app.vector.store import VectorPoint


def _retry_delay(attempt: int) -> int:
    return min(900, 15 * (2 ** max(0, attempt - 1)))


class KnowledgeReindexWorker:
    """Rebuilds Qdrant projections from PostgreSQL RAG chunks; never treats Qdrant as source of truth."""

    def __init__(self, *, governance: KnowledgeGovernanceRepository, rag_repository: RAGRepository,
                 embedder, vector_store, sparse_encoder=None):
        self.governance = governance
        self.rag_repository = rag_repository
        self.embedder = embedder
        self.vector_store = vector_store
        self.sparse_encoder = sparse_encoder or HashedBM25SparseEncoder()

    def process(self, job):
        if job.tenant_id != self.governance.tenant_id or job.tenant_id != self.rag_repository.tenant_id:
            raise PermissionError("cross-tenant knowledge reindex denied")
        if job.status not in {ReindexStatus.PENDING.value, ReindexStatus.RETRY.value}:
            return job
        version = self.governance.version(job.version_id)
        if version is None:
            raise ValueError("knowledge version missing for reindex job")
        document = self.governance.document(version.document_id)
        if document is None:
            raise ValueError("knowledge document missing for reindex job")
        job.status = ReindexStatus.RUNNING.value
        job.started_at = datetime.now(UTC)
        job.attempt_number += 1
        self.governance.session.flush()
        try:
            domain = RAGDomain(document.domain)
            if job.action == ReindexAction.DELETE.value:
                self.vector_store.delete_source(domain, tenant_id=job.tenant_id,
                                                source_id=version.rag_source_id,
                                                source_version=version.rag_source_version)
                self.rag_repository.deactivate_source(source_id=version.rag_source_id,
                                                      source_version=version.rag_source_version)
                job.stale_chunk_count = 0
            else:
                all_chunks = self.governance.chunks_for_version(version)
                indexable = [c for c in all_chunks if c.chunk_kind != "parent"]
                if not indexable:
                    raise ValueError("no authoritative RAG chunks available for governed knowledge version")
                if job.action == ReindexAction.INCREMENTAL.value:
                    stale_ids = set(self.governance.stale_chunk_ids(
                        version, embedding_model=job.embedding_model,
                        embedding_dimensions=job.embedding_dimensions, index_version=job.index_version))
                    indexable = [c for c in indexable if c.chunk_id in stale_ids]
                if indexable:
                    texts = [c.content_text for c in indexable]
                    vectors = self.embedder.embed(texts)
                    sparse_vectors = self.sparse_encoder.encode(texts)
                    collection = self.vector_store.ensure_domain(domain)
                    points, records = [], []
                    now = datetime.now(UTC)
                    existing_records = {
                        record.chunk_id: record for record in self.governance.current_projection_records(
                            version, embedding_model=job.embedding_model,
                            embedding_dimensions=job.embedding_dimensions,
                            index_version=job.index_version, active_only=False,
                        )
                    }
                    for chunk, vector, sparse in zip(indexable, vectors, sparse_vectors, strict=True):
                        point_id = QdrantVectorStore.point_id(chunk.chunk_id)
                        payload = {
                            **dict(chunk.payload_metadata or {}),
                            "chunk_id": chunk.chunk_id,
                            "parent_chunk_id": chunk.parent_chunk_id,
                            "chunk_kind": chunk.chunk_kind,
                            "text": chunk.content_text,
                            "citation": dict(chunk.citation or {}),
                            "metadata": dict(chunk.payload_metadata or {}),
                            "active": True,
                        }
                        points.append(VectorPoint(point_id=point_id, vector=vector, sparse_vector=sparse, payload=payload))
                        existing = existing_records.get(chunk.chunk_id)
                        if existing is not None:
                            existing.active = True
                            existing.indexed_at = now
                            existing.collection_name = collection
                            existing.point_id = point_id
                        else:
                            records.append(RAGIndexRecordModel(
                                index_record_id=f"ridx_{uuid5(NAMESPACE_URL, chunk.chunk_id + job.embedding_model + str(job.embedding_dimensions) + job.index_version).hex}",
                                tenant_id=job.tenant_id, claim_id=chunk.claim_id, chunk_id=chunk.chunk_id,
                                domain=chunk.domain, source_id=version.rag_source_id,
                                source_version=version.rag_source_version, collection_name=collection,
                                point_id=point_id, embedding_model=job.embedding_model,
                                embedding_dimensions=job.embedding_dimensions,
                                embedding_input_sha256=sha256(chunk.content_text.encode()).hexdigest(),
                                index_version=job.index_version, active=True, indexed_at=now,
                            ))
                    self.vector_store.upsert(domain, points)
                    self.rag_repository.deactivate_stale_projection_configs(
                        source_id=version.rag_source_id, source_version=version.rag_source_version,
                        keep_embedding_model=job.embedding_model,
                        keep_embedding_dimensions=job.embedding_dimensions,
                        keep_index_version=job.index_version,
                    )
                    self.rag_repository.add_index_records(records)
                job.stale_chunk_count = 0
            job.status = ReindexStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC)
            job.error_code = None
            job.error_sha256 = None
        except Exception as exc:
            job.error_code = type(exc).__name__
            job.error_sha256 = sha256(str(exc).encode()).hexdigest()
            if job.attempt_number >= job.max_attempts:
                job.status = ReindexStatus.DEAD_LETTER.value
            else:
                job.status = ReindexStatus.RETRY.value
                job.next_attempt_at = datetime.now(UTC) + timedelta(seconds=_retry_delay(job.attempt_number))
        self.governance.session.flush()
        return job
