from __future__ import annotations

from app.domain.advanced_rag import Answerability
from app.domain.multimodal_rag import EvidenceModality, InconsistencySeverity, MultimodalCandidate, MultimodalInconsistency, MultimodalKnowledgeGap, MultimodalRoute


class MultimodalGapDetector:
    def __init__(self, *, minimum_confidence: float = 0.50, minimum_citation_coverage: float = 0.80):
        self.minimum_confidence = minimum_confidence
        self.minimum_citation_coverage = minimum_citation_coverage

    def detect(
        self,
        *,
        route: MultimodalRoute,
        items: list[MultimodalCandidate],
        inconsistencies: tuple[MultimodalInconsistency, ...],
    ) -> tuple[tuple[MultimodalKnowledgeGap, ...], Answerability, float, float]:
        present = {item.modality for item in items}
        valid_citations = sum(1 for item in items if item.citation.validate()[0])
        citation_coverage = valid_citations / len(items) if items else 0.0
        required = set(route.required_modalities)
        modality_coverage = len(required & present) / len(required) if required else (len(present) / len(route.modalities) if route.modalities else 0.0)
        gaps: list[MultimodalKnowledgeGap] = []
        for modality in sorted(required - present, key=lambda x: x.value):
            gaps.append(MultimodalKnowledgeGap("missing_required_modality", f"Required {modality.value} evidence was not retrieved", True, modality))
        if not items:
            gaps.append(MultimodalKnowledgeGap("no_multimodal_evidence", "No eligible multimodal evidence was retrieved", True))
        if citation_coverage < self.minimum_citation_coverage:
            gaps.append(MultimodalKnowledgeGap("multimodal_citation_coverage", "Multimodal citation coverage is below the required threshold", True))
        if items and sum(x.confidence for x in items) / len(items) < self.minimum_confidence:
            gaps.append(MultimodalKnowledgeGap("low_multimodal_confidence", "Retrieved multimodal evidence confidence is too low", True))
        if any(x.severity == InconsistencySeverity.MATERIAL for x in inconsistencies):
            gaps.append(MultimodalKnowledgeGap("material_cross_modal_inconsistency", "Material evidence conflicts across modalities require human review", True))
        blocking = any(g.blocking for g in gaps)
        if not items or blocking:
            answerability = Answerability.INSUFFICIENT
        elif gaps:
            answerability = Answerability.PARTIAL
        else:
            answerability = Answerability.ANSWERABLE
        return tuple(gaps), answerability, round(modality_coverage, 6), round(citation_coverage, 6)
