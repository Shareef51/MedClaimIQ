from __future__ import annotations

from typing import Sequence

from app.domain.rag import QueryPlan, RetrievalAssessment, RetrievalHit


def assess_retrieval(
    hits: Sequence[RetrievalHit],
    *,
    plan: QueryPlan,
    minimum_confidence: float = 0.35,
) -> RetrievalAssessment:
    requested = set(plan.domains)
    observed = {hit.domain for hit in hits}
    domain_coverage = len(requested & observed) / max(1, len(requested))
    source_ids = {str(hit.metadata.get("source_id")) for hit in hits if hit.metadata.get("source_id")}
    source_diversity = min(1.0, len(source_ids) / max(1, min(3, len(hits)))) if hits else 0.0
    top_scores = [float(hit.rerank_score or hit.score) for hit in hits[:3]]
    relevance = sum(top_scores) / len(top_scores) if top_scores else 0.0
    confidence = max(0.0, min(1.0, 0.60 * relevance + 0.25 * domain_coverage + 0.15 * source_diversity))

    reasons: list[str] = []
    if not hits:
        reasons.append("no_candidates_after_security_and_metadata_filters")
    if hits and relevance < minimum_confidence:
        reasons.append("top_candidate_relevance_below_threshold")
    if requested and domain_coverage == 0:
        reasons.append("requested_domain_not_covered")
    no_evidence = not hits or confidence < minimum_confidence
    return RetrievalAssessment(
        confidence=confidence,
        coverage=domain_coverage,
        source_diversity=source_diversity,
        no_evidence=no_evidence,
        reasons=tuple(reasons),
    )
