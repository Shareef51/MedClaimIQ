from __future__ import annotations

from app.domain.cross_source_rag import EvidenceItem
from app.domain.grounding import CandidateStatement, CitationStatus, CitationVerification


class CitationVerifier:
    def verify(self, statement: CandidateStatement, evidence: tuple[EvidenceItem, ...]) -> CitationVerification:
        by_key = {item.evidence_key: item for item in evidence}
        if not statement.citations:
            return CitationVerification(CitationStatus.MISSING, (), (), ("statement_has_no_citation",))
        verified: list[str] = []
        invalid: list[str] = []
        reasons: list[str] = []
        for citation in statement.citations:
            item = by_key.get(citation.evidence_key)
            if item is None:
                invalid.append(citation.evidence_key)
                reasons.append("unknown_evidence_key")
                continue
            if citation.source_id is not None and citation.source_id != item.source_id:
                invalid.append(citation.evidence_key)
                reasons.append("source_id_mismatch")
                continue
            if citation.source_version is not None and citation.source_version != item.source_version:
                invalid.append(citation.evidence_key)
                reasons.append("source_version_mismatch")
                continue
            if citation.locator:
                actual = item.citation.locator or {}
                if any(actual.get(key) != value for key, value in citation.locator.items()):
                    invalid.append(citation.evidence_key)
                    reasons.append("citation_locator_mismatch")
                    continue
            verified.append(citation.evidence_key)
        if verified and not invalid:
            status = CitationStatus.VERIFIED
        elif verified:
            status = CitationStatus.PARTIAL
        else:
            status = CitationStatus.INVALID
        return CitationVerification(status, tuple(verified), tuple(invalid), tuple(dict.fromkeys(reasons)))
