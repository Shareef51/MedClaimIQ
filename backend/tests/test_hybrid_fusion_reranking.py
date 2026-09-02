from datetime import date

from app.domain.rag import QueryPlan, RAGDomain, RetrievalHit
from app.rag.assessment import assess_retrieval
from app.rag.compression import ContextualCompressor
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.reranking import EvidenceAwareReranker, diversify_candidates


def hit(chunk_id, *, score, source, authority=50, text="coverage evidence", domain=RAGDomain.POLICY):
    return RetrievalHit(
        chunk_id=chunk_id,
        domain=domain,
        score=score,
        text=text,
        parent_chunk_id=None,
        citation={"page_number": 2},
        metadata={
            "source_id": source,
            "authority_rank": authority,
            "evidence_confidence": 0.9,
            "service_date": "2026-08-10T00:00:00Z",
        },
    )


def plan():
    return QueryPlan(
        original_query="coverage 99213",
        normalized_query="coverage 99213",
        variants=("coverage 99213",),
        subqueries=("coverage 99213",),
        domains=(RAGDomain.POLICY,),
        exact_terms=("99213",),
        service_date_from=date(2026, 8, 10),
        service_date_to=date(2026, 8, 10),
        planner_version="test",
    )


def test_rrf_rewards_candidate_found_by_dense_and_sparse_lists():
    dense = [hit("both", score=0.9, source="a"), hit("dense", score=0.8, source="b")]
    sparse = [hit("both", score=12.0, source="a"), hit("sparse", score=10.0, source="c")]
    dense[0] = RetrievalHit(**{**dense[0].__dict__, "dense_score": 0.9, "retrieval_sources": ("dense",)})
    dense[1] = RetrievalHit(**{**dense[1].__dict__, "dense_score": 0.8, "retrieval_sources": ("dense",)})
    sparse[0] = RetrievalHit(**{**sparse[0].__dict__, "sparse_score": 12.0, "retrieval_sources": ("sparse",)})
    sparse[1] = RetrievalHit(**{**sparse[1].__dict__, "sparse_score": 10.0, "retrieval_sources": ("sparse",)})
    fused = reciprocal_rank_fusion([dense, sparse])
    assert fused[0].chunk_id == "both"
    assert set(fused[0].retrieval_sources) == {"dense", "sparse"}


def test_evidence_reranker_rewards_authority_exact_term_and_temporal_alignment():
    weak = hit("weak", score=0.02, source="weak", authority=20, text="coverage evidence")
    strong = hit("strong", score=0.02, source="strong", authority=95, text="coverage for CPT 99213")
    weak = RetrievalHit(**{**weak.__dict__, "fused_score": 0.03})
    strong = RetrievalHit(**{**strong.__dict__, "fused_score": 0.03})
    result = EvidenceAwareReranker().rerank("coverage 99213", [weak, strong], plan=plan())
    assert result[0].chunk_id == "strong"
    assert result[0].rerank_score > result[1].rerank_score


def test_diversification_prevents_single_source_monopoly():
    hits = [hit(f"a-{i}", score=1 - i / 10, source="source-a") for i in range(4)]
    hits += [hit("b-1", score=0.5, source="source-b")]
    diversified = diversify_candidates(hits, limit=3, max_per_source=2)
    assert {item.metadata["source_id"] for item in diversified} == {"source-a", "source-b"}


def test_context_compression_keeps_citation_and_relevant_sentence():
    text = "Unrelated sentence. " * 80 + "Prior authorization is required for CPT 99213. " + "Other text. " * 80
    original = hit("long", score=0.9, source="policy", text=text)
    compressed = ContextualCompressor(max_chars_per_hit=400, max_sentences=3).compress("prior authorization 99213", [original])[0]
    assert "99213" in compressed.text
    assert compressed.citation == original.citation
    assert compressed.metadata["context_compression"]["applied"] is True


def test_assessment_returns_explicit_no_evidence():
    assessment = assess_retrieval([], plan=plan())
    assert assessment.no_evidence is True
    assert "no_candidates_after_security_and_metadata_filters" in assessment.reasons
