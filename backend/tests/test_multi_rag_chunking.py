from datetime import date

from app.domain.rag import CitationAnchor, KnowledgeDocument, RAGDomain, SourceSegment
from app.rag.chunking import ParentChildChunker
from app.rag.source_builder import infer_rag_domain


def document(text: str, *, version: str = "1") -> KnowledgeDocument:
    return KnowledgeDocument(
        tenant_id="tenant-a",
        claim_id="claim-1",
        patient_subject_id="patient-1",
        domain=RAGDomain.EVIDENCE,
        source_type="evidence",
        source_id="ev-1",
        source_version=version,
        source_content_sha256="a" * 64,
        segments=(
            SourceSegment(
                segment_id="unit-1",
                text=text,
                unit_type="text",
                citation=CitationAnchor(evidence_id="ev-1", extraction_unit_id="unit-1", page_number=7, bbox=(1, 2, 3, 4)),
            ),
        ),
        authority_rank=75,
        evidence_confidence=0.91,
        entity_ids=("entity-2", "entity-1"),
        relationship_types=("derived_from",),
        acl_tags=("claim_authorized", "reviewer"),
        service_date=date(2026, 8, 10),
    )


def test_parent_child_chunking_is_deterministic_and_preserves_citation_and_acl():
    text = " ".join(f"token{i}" for i in range(800))
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=120, overlap_tokens=20)
    first = chunker.chunk(document(text))
    second = chunker.chunk(document(text))
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    parents = [item for item in first if item.parent_chunk_id is None]
    children = [item for item in first if item.parent_chunk_id is not None]
    assert parents and children
    assert all(item.citation["page_number"] == 7 for item in children)
    assert all(item.metadata["acl_tags"] == ["claim_authorized", "reviewer"] for item in children)
    assert all(item.metadata["service_date"].startswith("2026-08-10T00:00:00") for item in children)


def test_source_version_changes_chunk_identity():
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=120, overlap_tokens=20)
    v1 = chunker.chunk(document("alpha beta gamma " * 50, version="1"))
    v2 = chunker.chunk(document("alpha beta gamma " * 50, version="2"))
    assert v1[0].chunk_id != v2[0].chunk_id


def test_table_and_transcript_chunks_keep_semantic_kind():
    base = document("row one row two " * 100)
    table_doc = KnowledgeDocument(**{**base.__dict__, "segments": (SourceSegment(segment_id="t", text=base.segments[0].text, unit_type="table"),)})
    transcript_doc = KnowledgeDocument(**{**base.__dict__, "segments": (SourceSegment(segment_id="a", text=base.segments[0].text, unit_type="transcript"),)})
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=120, overlap_tokens=20)
    assert any(item.kind.value == "table" for item in chunker.chunk(table_doc))
    assert any(item.kind.value == "transcript" for item in chunker.chunk(transcript_doc))


def test_domain_inference_routes_expected_sources():
    assert infer_rag_domain(source_type="policy_document") is RAGDomain.POLICY
    assert infer_rag_domain(source_type="medical_invoice") is RAGDomain.INVOICE
    assert infer_rag_domain(source_type="FHIR ExplanationOfBenefit") is RAGDomain.HOSPITAL
    assert infer_rag_domain(source_type="CPT coding reference") is RAGDomain.CODING
    assert infer_rag_domain(source_type="historical prior_claim") is RAGDomain.HISTORICAL_CLAIMS
    assert infer_rag_domain(source_type="claim form") is RAGDomain.CLAIM
    assert infer_rag_domain(source_type="user upload") is RAGDomain.EVIDENCE
