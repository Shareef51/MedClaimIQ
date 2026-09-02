from __future__ import annotations

from typing import Sequence

from app.domain.advanced_rag import Answerability, AdvancedQueryPlan, GapSeverity, KnowledgeGap
from app.domain.rag import RetrievalAssessment, RetrievalHit


class KnowledgeGapDetector:
    version = "knowledge-gap-detector-v1"

    def __init__(self, *, minimum_confidence: float = 0.55, minimum_citation_coverage: float = 0.80) -> None:
        self.minimum_confidence = minimum_confidence
        self.minimum_citation_coverage = minimum_citation_coverage

    def detect(
        self,
        *,
        plan: AdvancedQueryPlan,
        hits: Sequence[RetrievalHit],
        assessment: RetrievalAssessment,
        citation_coverage: float,
    ) -> tuple[tuple[KnowledgeGap, ...], Answerability]:
        gaps: list[KnowledgeGap] = []
        if assessment.no_evidence or not hits:
            gaps.append(KnowledgeGap("no_evidence", GapSeverity.BLOCKING, "No authorized, governed evidence satisfied the retrieval plan.", recommended_action="human_review_or_request_evidence"))
        found_domains = {hit.domain for hit in hits}
        for domain in plan.query_plan.domains:
            if domain not in found_domains:
                gaps.append(KnowledgeGap("missing_domain_evidence", GapSeverity.WARNING, f"No selected evidence from requested domain '{domain.value}'.", domain=domain, recommended_action="retrieve_more"))
        if assessment.confidence < self.minimum_confidence:
            gaps.append(KnowledgeGap("low_retrieval_confidence", GapSeverity.WARNING, f"Retrieval confidence {assessment.confidence:.3f} is below {self.minimum_confidence:.3f}.", recommended_action="retrieve_more_or_human_review"))
        if citation_coverage < self.minimum_citation_coverage:
            gaps.append(KnowledgeGap("citation_coverage", GapSeverity.BLOCKING, f"Citation coverage {citation_coverage:.3f} is below {self.minimum_citation_coverage:.3f}.", recommended_action="do_not_generate_material_claims"))
        for exact in plan.query_plan.exact_terms:
            if hits and not any(exact.lower() in hit.text.lower() for hit in hits):
                gaps.append(KnowledgeGap("exact_term_not_grounded", GapSeverity.BLOCKING, f"Exact requested code/term '{exact}' is not present in selected evidence.", recommended_action="retrieve_exact_term_or_human_review"))

        if any(g.severity == GapSeverity.BLOCKING for g in gaps):
            return tuple(gaps), Answerability.INSUFFICIENT
        if gaps:
            return tuple(gaps), Answerability.PARTIAL
        return tuple(), Answerability.ANSWERABLE
