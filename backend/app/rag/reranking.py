from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
from typing import Sequence

from app.domain.rag import QueryPlan, RetrievalHit

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.:-][a-z0-9]+)*", re.IGNORECASE)


def _terms(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}


class EvidenceAwareReranker:
    version = "evidence-aware-reranker-v1"

    def rerank(self, query: str, hits: Sequence[RetrievalHit], *, plan: QueryPlan) -> list[RetrievalHit]:
        qterms = _terms(query)
        reranked: list[RetrievalHit] = []
        max_rrf = max((hit.fused_score or 0.0 for hit in hits), default=0.0) or 1.0
        for hit in hits:
            hterms = _terms(hit.text)
            lexical = len(qterms & hterms) / max(1, len(qterms))
            authority = max(0.0, min(1.0, float(hit.metadata.get("authority_rank", 0) or 0) / 100.0))
            evidence_conf = max(0.0, min(1.0, float(hit.metadata.get("evidence_confidence", 0) or 0)))
            fused = (hit.fused_score or 0.0) / max_rrf
            exact_bonus = 0.0
            lowered = hit.text.lower()
            if plan.exact_terms and all(term.lower() in lowered for term in plan.exact_terms):
                exact_bonus = 0.08
            temporal_bonus = self._temporal_bonus(hit, plan)
            score = min(
                1.0,
                0.45 * fused
                + 0.22 * lexical
                + 0.15 * authority
                + 0.10 * evidence_conf
                + exact_bonus
                + temporal_bonus,
            )
            metadata = dict(hit.metadata)
            metadata["rerank_features"] = {
                "fused": round(fused, 6),
                "lexical_overlap": round(lexical, 6),
                "authority": round(authority, 6),
                "evidence_confidence": round(evidence_conf, 6),
                "exact_term_bonus": exact_bonus,
                "temporal_bonus": temporal_bonus,
            }
            reranked.append(replace(hit, score=score, rerank_score=score, metadata=metadata))
        reranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return reranked

    @staticmethod
    def _temporal_bonus(hit: RetrievalHit, plan: QueryPlan) -> float:
        if not (plan.service_date_from or plan.service_date_to):
            return 0.0
        raw = hit.metadata.get("service_date")
        if not raw:
            return 0.0
        try:
            value = date.fromisoformat(str(raw)[:10])
        except ValueError:
            return 0.0
        if plan.service_date_from and value < plan.service_date_from:
            return 0.0
        if plan.service_date_to and value > plan.service_date_to:
            return 0.0
        return 0.05


def diversify_candidates(
    hits: Sequence[RetrievalHit],
    *,
    limit: int,
    max_per_source: int = 2,
) -> list[RetrievalHit]:
    if limit <= 0:
        return []
    selected: list[RetrievalHit] = []
    source_counts: dict[str, int] = {}
    deferred: list[RetrievalHit] = []
    for hit in hits:
        source = str(hit.metadata.get("source_id") or hit.chunk_id)
        if source_counts.get(source, 0) >= max_per_source:
            deferred.append(hit)
            continue
        selected.append(hit)
        source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            return selected
    for hit in deferred:
        if len(selected) >= limit:
            break
        selected.append(hit)
    return selected
