from app.domain.rag import KnowledgeDocument, RAGDomain, RetrievalHit, RetrievalScope, SourceSegment
from app.rag.chunking import ParentChildChunker
from app.services.rag import DenseRetrievalService, RAGIndexingService, retry_delay_seconds
from app.vector.qdrant_store import QdrantVectorStore


class FakeEmbedder:
    def __init__(self): self.calls = []
    def embed(self, texts):
        self.calls.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


class FakeVectorStore:
    def __init__(self):
        self.deleted = []
        self.points = []
        self.query_hits = []
    def ensure_domain(self, domain): return f"collection_{domain.value}"
    def upsert(self, domain, points): self.points.extend(points)
    def delete_source(self, domain, *, tenant_id, source_id, source_version=None): self.deleted.append((domain.value, tenant_id, source_id, source_version))
    def query(self, domain, *, vector, scope, limit): return list(self.query_hits)


class Parent:
    def __init__(self, text): self.content_text = text


class FakeRepo:
    tenant_id = "tenant-a"
    def __init__(self):
        self.chunks = []
        self.records = []
        self.deactivated = []
    def save_chunks(self, chunks): self.chunks.extend(chunks); return chunks
    def deactivate_other_source_versions(self, **kwargs): self.deactivated.append(kwargs)
    def add_index_records(self, records): self.records.extend(records)
    def deactivate_source(self, **kwargs): self.deactivated.append(kwargs)
    def deactivate_stale_index_versions(self, **kwargs): self.deactivated.append(kwargs)
    def parent_chunks(self, ids): return {item: Parent("hydrated parent context") for item in ids}


def doc():
    return KnowledgeDocument(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        domain=RAGDomain.POLICY, source_type="policy", source_id="policy-1", source_version="3",
        source_content_sha256="a" * 64, segments=(SourceSegment(segment_id="s1", text="coverage terms " * 100),),
        authority_rank=90, evidence_confidence=0.95, entity_ids=("policy-entity",), acl_tags=("claim_authorized",),
    )


def test_indexing_indexes_children_not_parent_and_reindex_deletes_old_projection():
    repo, vectors, embedder = FakeRepo(), FakeVectorStore(), FakeEmbedder()
    service = RAGIndexingService(
        repository=repo, chunker=ParentChildChunker(parent_tokens=500, child_tokens=120, overlap_tokens=20),
        embedder=embedder, vector_store=vectors, embedding_model="fake", embedding_dimensions=2, index_version="v1",
    )
    result = service.index_document(doc(), replace_previous_versions=True)
    assert result.chunks_persisted > result.vectors_upserted > 0
    assert vectors.deleted == [("policy", "tenant-a", "policy-1", None)]
    assert all(point.payload["tenant_id"] == "tenant-a" for point in vectors.points)
    assert all(point.payload["acl_tags"] == ["claim_authorized"] for point in vectors.points)
    assert all(point.payload["parent_chunk_id"] for point in vectors.points)
    assert len(repo.records) == result.vectors_upserted


def test_dense_retrieval_hydrates_parent_but_keeps_matched_child():
    repo, vectors, embedder = FakeRepo(), FakeVectorStore(), FakeEmbedder()
    vectors.query_hits = [RetrievalHit(
        chunk_id="child-1", domain=RAGDomain.POLICY, score=0.91, text="matched child",
        parent_chunk_id="parent-1", citation={"page_number": 4}, metadata={"tenant_id": "tenant-a"},
    )]
    service = DenseRetrievalService(embedder=embedder, vector_store=vectors, repository=repo)
    hits = service.search(query="coverage", scope=RetrievalScope(tenant_id="tenant-a", claim_id="claim-1", domains=(RAGDomain.POLICY,)))
    assert hits[0].text == "hydrated parent context"
    assert hits[0].metadata["matched_child_text"] == "matched child"
    assert hits[0].citation["page_number"] == 4


def test_dense_retrieval_denies_cross_tenant_scope():
    service = DenseRetrievalService(embedder=FakeEmbedder(), vector_store=FakeVectorStore(), repository=FakeRepo())
    try:
        service.search(query="x", scope=RetrievalScope(tenant_id="tenant-b", claim_id="claim-1"))
        assert False, "expected PermissionError"
    except PermissionError:
        pass


def test_retry_backoff_is_bounded():
    assert retry_delay_seconds(attempt=1) == 15
    assert retry_delay_seconds(attempt=2) == 30
    assert retry_delay_seconds(attempt=20) == 600


def test_qdrant_point_id_and_collection_name_are_stable_without_live_server():
    fake_client = object()
    store = QdrantVectorStore(url="http://unused", api_key=None, collection_prefix="medclaimiq", index_version="rag-v1", dimensions=1536, client=fake_client)
    assert store.point_id("chunk-1") == store.point_id("chunk-1")
    assert store.point_id("chunk-1") != store.point_id("chunk-2")
    assert store.collection_name(RAGDomain.CLAIM) == "medclaimiq_claim_rag_v1"
