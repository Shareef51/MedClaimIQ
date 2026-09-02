from app.domain.rag import RAGDomain, RetrievalHit, RetrievalScope, RetrievalStrategy
from app.services.rag import HybridRetrievalService
from app.sparse.provider import HashedBM25SparseEncoder


class FakeEmbedder:
    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


class Parent:
    def __init__(self, content_text):
        self.content_text = content_text


class FakeRepo:
    tenant_id = "tenant-a"
    def parent_chunks(self, ids):
        return {item: Parent("parent coverage context for CPT 99213") for item in ids}


class FakeTelemetry:
    def __init__(self): self.calls = []
    def record(self, **kwargs): self.calls.append(kwargs)


class FakeHybridStore:
    def __init__(self, *, policy=True, evidence=False):
        self.policy = policy
        self.evidence = evidence
        self.scopes = []
    def query(self, domain, *, vector, scope, limit):
        return self.query_dense(domain, vector=vector, scope=scope, limit=limit)
    def query_dense(self, domain, *, vector, scope, limit):
        self.scopes.append(scope)
        if domain is RAGDomain.POLICY and self.policy:
            return [RetrievalHit(
                chunk_id="policy-child", domain=domain, score=0.88,
                text="CPT 99213 requires prior authorization", parent_chunk_id="policy-parent",
                citation={"page_number": 8},
                metadata={"tenant_id": "tenant-a", "claim_id": "claim-1", "source_id": "policy-1", "authority_rank": 95, "evidence_confidence": 0.98},
                dense_score=0.88, retrieval_sources=("dense",),
            )]
        if domain is RAGDomain.EVIDENCE and self.evidence:
            return [RetrievalHit(
                chunk_id="evidence-child", domain=domain, score=0.7,
                text="uploaded authorization document", parent_chunk_id=None,
                citation={"page_number": 1},
                metadata={"tenant_id": "tenant-a", "claim_id": "claim-1", "source_id": "ev-1", "authority_rank": 60, "evidence_confidence": 0.8},
                dense_score=0.7, retrieval_sources=("dense",),
            )]
        return []
    def query_sparse(self, domain, *, vector, scope, limit):
        self.scopes.append(scope)
        if domain is RAGDomain.POLICY and self.policy:
            return [RetrievalHit(
                chunk_id="policy-child", domain=domain, score=8.0,
                text="CPT 99213 requires prior authorization", parent_chunk_id="policy-parent",
                citation={"page_number": 8},
                metadata={"tenant_id": "tenant-a", "claim_id": "claim-1", "source_id": "policy-1", "authority_rank": 95, "evidence_confidence": 0.98},
                sparse_score=8.0, retrieval_sources=("sparse",),
            )]
        return []


def scope(domains=()):
    return RetrievalScope(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        domains=domains, acl_tags=("claim_authorized",), minimum_authority_rank=80,
    )


def test_hybrid_service_fuses_hydrates_and_records_telemetry():
    telemetry = FakeTelemetry()
    store = FakeHybridStore(policy=True)
    service = HybridRetrievalService(
        embedder=FakeEmbedder(), vector_store=store, repository=FakeRepo(),
        sparse_encoder=HashedBM25SparseEncoder(), telemetry=telemetry,
    )
    result = service.search(
        query="Does CPT 99213 require prior authorization?",
        scope=scope(), limit=3, strategy=RetrievalStrategy.HYBRID,
    )
    assert result.hits
    assert result.hits[0].domain is RAGDomain.POLICY
    assert result.hits[0].metadata["matched_child_text"].startswith("CPT 99213")
    assert set(result.hits[0].retrieval_sources) == {"dense", "sparse"}
    assert telemetry.calls and telemetry.calls[0]["assessment"].no_evidence is False
    assert all(item.tenant_id == "tenant-a" and item.claim_id == "claim-1" for item in store.scopes)
    assert all(item.minimum_authority_rank == 80 for item in store.scopes)


def test_hybrid_service_safe_domain_fallback_never_relaxes_security_scope():
    store = FakeHybridStore(policy=False, evidence=True)
    service = HybridRetrievalService(embedder=FakeEmbedder(), vector_store=store, repository=FakeRepo())
    result = service.search(query="policy coverage", scope=scope(), limit=2)
    assert "expanded_to_all_authorized_domains" in result.fallback_steps
    assert result.hits[0].domain is RAGDomain.EVIDENCE
    assert all(item.tenant_id == "tenant-a" and item.claim_id == "claim-1" for item in store.scopes)
    assert all(item.acl_tags == ("claim_authorized",) for item in store.scopes)


def test_hybrid_service_denies_cross_tenant_scope():
    service = HybridRetrievalService(embedder=FakeEmbedder(), vector_store=FakeHybridStore(), repository=FakeRepo())
    try:
        service.search(query="coverage", scope=RetrievalScope(tenant_id="tenant-b", claim_id="claim-1"))
        assert False, "expected PermissionError"
    except PermissionError:
        pass
