from __future__ import annotations

import re
from dataclasses import replace
from typing import Sequence

from app.domain.advanced_rag import AdvancedQueryPlan
from app.domain.rag import RetrievalHit

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.:-][a-z0-9]+)*", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text)}


class AdvancedEvidenceReranker:
    """Second-stage deterministic reranker over already security-filtered candidates."""

    version = "advanced-evidence-reranker-v2"

    def rerank(self, *, query: str, hits: Sequence[RetrievalHit], plan: AdvancedQueryPlan) -> list[RetrievalHit]:
        qterms = _tokens(query)
        output: list[RetrievalHit] = []
        for hit in hits:
            terms = _tokens(hit.text)
            lexical = len(qterms & terms) / max(1, len(qterms))
            citation = hit.citation or {}
            citation_quality = 1.0 if any(citation.get(k) is not None for k in ("page_number", "start_ms", "bbox", "source_locator", "evidence_id")) else 0.0
            authority = min(1.0, max(0.0, float(hit.metadata.get("authority_rank", 0) or 0) / 100.0))
            evidence_conf = min(1.0, max(0.0, float(hit.metadata.get("evidence_confidence", 0) or 0)))
            prior = float(hit.rerank_score if hit.rerank_score is not None else hit.score)
            exact = 1.0 if plan.query_plan.exact_terms and all(t.lower() in hit.text.lower() for t in plan.query_plan.exact_terms) else 0.0
            score = min(1.0, 0.50 * prior + 0.16 * lexical + 0.12 * authority + 0.10 * evidence_conf + 0.07 * citation_quality + 0.05 * exact)
            metadata = dict(hit.metadata)
            metadata["advanced_rerank_features"] = {
                "prior": round(prior, 6),
                "lexical": round(lexical, 6),
                "authority": round(authority, 6),
                "evidence_confidence": round(evidence_conf, 6),
                "citation_quality": citation_quality,
                "exact_term_match": exact,
            }
            output.append(replace(hit, score=score, rerank_score=score, metadata=metadata))
        output.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)
        return self._mmr_like_diversify(output)

    @staticmethod
    def _mmr_like_diversify(hits: list[RetrievalHit]) -> list[RetrievalHit]:
        # Preserve score order but avoid allowing a single source to occupy the entire prefix.
        selected: list[RetrievalHit] = []
        deferred: list[RetrievalHit] = []
        source_count: dict[str, int] = {}
        for hit in hits:
            source = str(hit.metadata.get("source_id") or hit.chunk_id)
            if source_count.get(source, 0) >= 2:
                deferred.append(hit)
                continue
            selected.append(hit)
            source_count[source] = source_count.get(source, 0) + 1
        return selected + deferred
