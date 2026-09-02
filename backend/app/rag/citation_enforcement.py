from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from app.domain.advanced_rag import CitationCheck
from app.domain.rag import RetrievalHit


class CitationEnforcer:
    version = "retrieval-citation-enforcer-v1"

    def verify(self, hits: Sequence[RetrievalHit], *, strict: bool = True) -> tuple[list[RetrievalHit], tuple[CitationCheck, ...], float]:
        checks: list[CitationCheck] = []
        accepted: list[RetrievalHit] = []
        for hit in hits:
            reasons: list[str] = []
            source_id = str(hit.metadata.get("source_id")) if hit.metadata.get("source_id") else None
            source_version = str(hit.metadata.get("source_version")) if hit.metadata.get("source_version") else None
            citation = hit.citation or {}
            if not source_id:
                reasons.append("missing_source_id")
            if source_version is None:
                reasons.append("missing_source_version")
            if not citation:
                reasons.append("missing_citation")
            elif not any(citation.get(key) not in (None, {}, [], "") for key in ("page_number", "start_ms", "bbox", "source_locator", "evidence_id", "extraction_unit_id")):
                reasons.append("missing_citation_locator")
            valid = not reasons
            checks.append(CitationCheck(hit.chunk_id, valid, tuple(reasons), source_id, source_version))
            if valid or not strict:
                metadata = dict(hit.metadata)
                metadata["citation_enforcement"] = {"valid": valid, "reasons": reasons, "version": self.version}
                accepted.append(replace(hit, metadata=metadata))
        coverage = sum(1 for c in checks if c.valid) / max(1, len(checks))
        return accepted, tuple(checks), round(coverage, 6)
