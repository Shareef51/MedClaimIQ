from __future__ import annotations

import json
from pathlib import Path

from app.domain.rag import CitationAnchor, KnowledgeDocument, RAGDomain, SourceSegment
from app.rag.chunking import ParentChildChunker

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "sample-data" / "rag_knowledge_seed.json"


def main() -> None:
    payload = json.loads(SEED.read_text())
    if payload.get("data_classification") != "synthetic_only":
        raise RuntimeError("RAG preview seed must be synthetic_only")
    chunker = ParentChildChunker()
    for item in payload["documents"]:
        segments = tuple(
            SourceSegment(
                segment_id=segment["segment_id"],
                text=segment["text"],
                unit_type=segment["unit_type"],
                citation=CitationAnchor(page_number=segment.get("page_number")),
            )
            for segment in item["segments"]
        )
        document = KnowledgeDocument(
            tenant_id=payload["tenant_id"],
            claim_id=payload["claim_id"],
            patient_subject_id=payload["patient_subject_id"],
            domain=RAGDomain(item["domain"]),
            source_type=item["source_type"],
            source_id=item["source_id"],
            source_version=item["source_version"],
            source_content_sha256=None,
            segments=segments,
            authority_rank=item["authority_rank"],
            evidence_confidence=item["evidence_confidence"],
            acl_tags=tuple(item["acl_tags"]),
        )
        chunks = chunker.chunk(document)
        print(f"{item['domain']}: {len(chunks)} chunks")
        for chunk in chunks:
            print(f"  {chunk.kind.value:10s} {chunk.chunk_id} page={chunk.citation.get('page_number')}")


if __name__ == "__main__":
    main()
