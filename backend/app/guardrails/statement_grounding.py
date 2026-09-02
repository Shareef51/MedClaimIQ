from __future__ import annotations

import re
from collections import Counter

from app.domain.cross_source_rag import ContradictionSummary, EvidenceItem
from app.domain.grounding import (
    CandidateStatement, CitationStatus, StatementGrounding, StatementSupport,
)
from app.guardrails.citations import CitationVerifier

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*")
_NUMBER_RE = re.compile(r"(?<![A-Za-z])\$?\d+(?:\.\d+)?%?")
_CODE_RE = re.compile(r"\b(?:[A-Z]\d{2}(?:\.\w+)?|\d{5}|[A-Z]\d{4})\b", re.I)
_STOP = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or", "in", "on", "for", "with", "by", "from", "this", "that", "claim"}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 2 and token.lower() not in _STOP]


def _overlap(statement: str, evidence_text: str) -> float:
    left = Counter(_tokens(statement))
    right = Counter(_tokens(evidence_text))
    if not left:
        return 0.0
    matched = sum(min(count, right[token]) for token, count in left.items())
    return matched / max(1, sum(left.values()))


def _all_literals_present(pattern: re.Pattern[str], statement: str, evidence_text: str) -> bool:
    values = {match.group(0).lower().replace("$", "") for match in pattern.finditer(statement)}
    if not values:
        return True
    haystack = evidence_text.lower().replace("$", "")
    return all(value in haystack for value in values)


class UnsupportedClaimDetector:
    def __init__(self, *, minimum_overlap: float = 0.22) -> None:
        self.minimum_overlap = minimum_overlap
        self.citations = CitationVerifier()

    def check(
        self,
        statement: CandidateStatement,
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[ContradictionSummary, ...] = (),
    ) -> StatementGrounding:
        citation = self.citations.verify(statement, evidence)
        by_key = {item.evidence_key: item for item in evidence}
        cited = [by_key[key] for key in citation.verified_evidence_keys if key in by_key]
        combined = "\n".join(item.text for item in cited)
        overlap = _overlap(statement.text, combined) if cited else 0.0
        numeric_ok = _all_literals_present(_NUMBER_RE, statement.text, combined) if cited else not bool(_NUMBER_RE.search(statement.text))
        code_ok = _all_literals_present(_CODE_RE, statement.text, combined) if cited else not bool(_CODE_RE.search(statement.text))
        contradiction_safe = self._contradiction_safe(statement.text, contradictions)
        reasons: list[str] = list(citation.reasons)
        if overlap < self.minimum_overlap:
            reasons.append("insufficient_semantic_lexical_support")
        if not numeric_ok:
            reasons.append("numeric_value_not_supported_by_cited_evidence")
        if not code_ok:
            reasons.append("medical_code_not_supported_by_cited_evidence")
        if not contradiction_safe:
            reasons.append("statement_suppresses_material_contradiction")
        if not contradiction_safe:
            support = StatementSupport.CONTRADICTED
        elif citation.status in {CitationStatus.MISSING, CitationStatus.INVALID}:
            support = StatementSupport.UNSUPPORTED
        elif overlap >= self.minimum_overlap and numeric_ok and code_ok:
            support = StatementSupport.SUPPORTED if citation.status == CitationStatus.VERIFIED else StatementSupport.PARTIAL
        elif overlap >= self.minimum_overlap * 0.6 and cited:
            support = StatementSupport.PARTIAL
        else:
            support = StatementSupport.UNSUPPORTED
        score = overlap
        if citation.status == CitationStatus.VERIFIED:
            score = min(1.0, score + 0.20)
        if numeric_ok and code_ok:
            score = min(1.0, score + 0.10)
        if not contradiction_safe:
            score *= 0.25
        return StatementGrounding(
            statement_id=statement.statement_id,
            statement_sha256=statement.sha256,
            support=support,
            support_score=round(max(0.0, min(1.0, score)), 5),
            citation=citation,
            numeric_integrity=numeric_ok,
            medical_code_integrity=code_ok,
            contradiction_safe=contradiction_safe,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    @staticmethod
    def _contradiction_safe(text: str, contradictions: tuple[ContradictionSummary, ...]) -> bool:
        lower = text.lower()
        conflict_language = any(word in lower for word in ("conflict", "contradict", "mismatch", "discrepancy", "differs"))
        for contradiction in contradictions:
            if contradiction.severity != "material" or contradiction.status != "open":
                continue
            left = str(contradiction.left_value).lower()
            right = str(contradiction.right_value).lower()
            mentions_left = bool(left) and left in lower
            mentions_right = bool(right) and right in lower
            mentions_field = contradiction.field_name.lower().replace("_", " ") in lower
            if (mentions_left ^ mentions_right) and not conflict_language:
                return False
            if mentions_field and not conflict_language and (mentions_left or mentions_right):
                return False
        return True
