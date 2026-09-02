from app.domain.rag import KnowledgeDocument, RAGDomain, SourceSegment
from app.rag.chunking import ParentChildChunker
from app.services.rag import RAGIndexingService


class FakeEmbedder:
    def embed(self, texts): return [[1.0, 2.0] for _ in texts]


class FakeStore:
    def __init__(self): self.points=[]
    def ensure_domain(self, domain): return "hybrid"
    def upsert(self, domain, points): self.points.extend(points)
    def delete_source(self, *args, **kwargs): pass


class Repo:
    tenant_id="tenant-a"
    def save_chunks(self, chunks): return chunks
    def deactivate_other_source_versions(self, **kwargs): pass
    def deactivate_stale_index_versions(self, **kwargs): pass
    def add_index_records(self, records): pass


def test_indexing_projects_dense_and_sparse_vectors_together():
    document = KnowledgeDocument(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        domain=RAGDomain.CODING, source_type="coding_reference", source_id="cpt", source_version="1",
        source_content_sha256="a"*64, segments=(SourceSegment(segment_id="1", text="CPT 99213 office visit "*80),),
        authority_rank=100, evidence_confidence=1.0,
    )
    store=FakeStore()
    service=RAGIndexingService(
        repository=Repo(), chunker=ParentChildChunker(parent_tokens=500, child_tokens=120, overlap_tokens=20),
        embedder=FakeEmbedder(), vector_store=store, embedding_model="fake", embedding_dimensions=2, index_version="hybrid-v1",
    )
    result=service.index_document(document, replace_previous_versions=False)
    assert result.vectors_upserted == len(store.points) > 0
    assert all(point.sparse_vector is not None and point.sparse_vector.indices for point in store.points)
