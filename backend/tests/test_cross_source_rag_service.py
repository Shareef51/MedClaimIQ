from types import SimpleNamespace
from decimal import Decimal

from app.domain.cross_source_rag import RetrieverKind
from app.domain.rag import RAGDomain, RetrievalHit, RetrievalScope
from app.services.cross_source_rag import CrossSourceEvidenceService


class FakeRepo:
    tenant_id = "tenant-a"
    def structured_rows(self, plan):
        from app.domain.cross_source_rag import StructuredFact
        return {StructuredFact.CLAIM: [SimpleNamespace(claim_id="claim-1", status="verifying", total_amount=Decimal("100"), currency="USD", service_from="2026-08-10", service_to=None, policy_id=None, encounter_id=None)]}
    def fhir_snapshots(self, plan): return []
    def claim_entities(self, claim_id, limit=50): return []
    def graph_edges_for_claim(self, *args, **kwargs): return []
    def open_contradictions(self, claim_id, limit=100): return []
    def save_evidence_pack(self, pack, **kwargs): self.saved = (pack, kwargs)


class FakeHybrid:
    def search(self, **kwargs):
        hit = RetrievalHit(
            chunk_id="chunk-1", domain=RAGDomain.EVIDENCE, score=.8, text="uploaded evidence",
            parent_chunk_id=None, citation={"page_number":1},
            metadata={"source_type":"accepted_original_evidence", "source_id":"ev-1", "source_version":"1", "authority_rank":80, "evidence_confidence":.9, "entity_ids":["ce-1"]},
        )
        return SimpleNamespace(hits=(hit,))


def test_cross_source_service_fuses_sql_and_vector_and_hashes_query_for_persistence():
    repo = FakeRepo()
    result = CrossSourceEvidenceService(repository=repo, hybrid_retriever=FakeHybrid()).search(
        query="show evidence", scope=RetrievalScope(tenant_id="tenant-a", claim_id="claim-1"),
        requested_retrievers=(RetrieverKind.SQL, RetrieverKind.VECTOR), top_k=5,
    )
    assert {item.retriever for item in result.pack.items} == {RetrieverKind.SQL, RetrieverKind.VECTOR}
    assert len(repo.saved[1]["query_sha256"]) == 64
    assert repo.saved[1]["query_length"] == len("show evidence")


def test_cross_source_service_denies_cross_tenant_scope():
    try:
        CrossSourceEvidenceService(repository=FakeRepo()).search(
            query="claim", scope=RetrievalScope(tenant_id="tenant-b", claim_id="claim-1"),
            requested_retrievers=(RetrieverKind.SQL,),
        )
        assert False, "expected PermissionError"
    except PermissionError:
        pass
