from types import SimpleNamespace

from app.workers.knowledge_reindex import KnowledgeReindexWorker


class Gov:
    tenant_id = "t1"
    class S:
        def flush(self): pass
    session = S()
    def version(self, version_id):
        return SimpleNamespace(version_id=version_id, document_id="d1", rag_source_id="s1", rag_source_version="v1")
    def document(self, document_id): return SimpleNamespace(document_id=document_id, domain="policy")
    def chunks_for_version(self, version): return []
    def stale_chunk_ids(self, version, **kwargs): return []


class RagRepo:
    tenant_id = "t1"
    def __init__(self): self.deleted = False
    def deactivate_source(self, **kwargs): self.deleted = True
    def deactivate_stale_index_versions(self, **kwargs): pass
    def add_index_records(self, records): pass


class Vector:
    def __init__(self): self.deleted = False
    def delete_source(self, *args, **kwargs): self.deleted = True
    def ensure_domain(self, domain): return "collection"
    def upsert(self, domain, points): pass


class Embed:
    def embed(self, texts): return [[0.1, 0.2] for _ in texts]


def test_delete_job_propagates_retirement_to_qdrant_and_postgres_projection():
    rag = RagRepo(); vector = Vector()
    worker = KnowledgeReindexWorker(governance=Gov(), rag_repository=rag, embedder=Embed(), vector_store=vector)
    job = SimpleNamespace(tenant_id="t1", version_id="v1", action="delete", status="pending", attempt_number=0,
                          max_attempts=3, embedding_model="embed", embedding_dimensions=2, index_version="v2",
                          started_at=None, completed_at=None, error_code=None, error_sha256=None, next_attempt_at=None,
                          stale_chunk_count=1)
    result = worker.process(job)
    assert result.status == "completed"
    assert vector.deleted and rag.deleted
