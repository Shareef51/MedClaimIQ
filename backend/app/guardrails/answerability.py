from __future__ import annotations

from app.domain.cross_source_rag import EvidencePack
from app.domain.grounding import AnswerabilityAssessment, EvidenceQualityAssessment, ScreenedEvidence


class EvidenceQualityGate:
    def __init__(
        self,
        *,
        minimum_item_confidence: float = 0.55,
        minimum_authority_rank: int = 60,
        minimum_quality_score: float = 0.50,
    ) -> None:
        self.minimum_item_confidence = minimum_item_confidence
        self.minimum_authority_rank = minimum_authority_rank
        self.minimum_quality_score = minimum_quality_score

    def assess(self, pack: EvidencePack, screened: ScreenedEvidence) -> EvidenceQualityAssessment:
        safe = screened.safe_items
        qualifying = [
            item for item in safe
            if item.confidence >= self.minimum_item_confidence and item.authority_rank >= self.minimum_authority_rank
        ]
        authoritative = [item for item in safe if item.authority_rank >= 80]
        source_types = {item.source_type for item in safe}
        evidence_component = min(1.0, len(qualifying) / 3.0)
        authority_component = min(1.0, len(authoritative) / 2.0)
        diversity_component = min(1.0, len(source_types) / 3.0)
        pack_component = max(0.0, min(1.0, pack.assessment.confidence))
        score = 0.35 * pack_component + 0.30 * evidence_component + 0.20 * authority_component + 0.15 * diversity_component
        material = pack.assessment.unresolved_material_contradictions
        if material:
            score *= max(0.45, 1.0 - min(0.45, 0.15 * material))
        if screened.excluded_evidence_keys:
            score *= max(0.60, 1.0 - min(0.30, 0.10 * len(screened.excluded_evidence_keys)))
        reasons: list[str] = []
        if not safe:
            reasons.append("no_safe_evidence")
        if len(qualifying) < 1:
            reasons.append("no_qualifying_evidence")
        if len(authoritative) < 1:
            reasons.append("no_high_authority_evidence")
        if len(source_types) < 2 and len(safe) > 1:
            reasons.append("limited_source_diversity")
        if material:
            reasons.append("unresolved_material_contradictions")
        if screened.excluded_evidence_keys:
            reasons.append("retrieved_prompt_injection_risk")
        return EvidenceQualityAssessment(
            score=round(max(0.0, min(1.0, score)), 5),
            qualifying_evidence_count=len(qualifying),
            authoritative_evidence_count=len(authoritative),
            source_type_count=len(source_types),
            excluded_injection_count=len(screened.excluded_evidence_keys),
            unresolved_material_contradictions=material,
            reasons=tuple(reasons),
        )


class AnswerabilityGate:
    def __init__(self, *, minimum_quality_score: float = 0.50, minimum_pack_coverage: float = 0.50) -> None:
        self.minimum_quality_score = minimum_quality_score
        self.minimum_pack_coverage = minimum_pack_coverage

    def assess(self, pack: EvidencePack, quality: EvidenceQualityAssessment) -> AnswerabilityAssessment:
        reasons: list[str] = []
        if pack.assessment.no_evidence:
            reasons.append("evidence_pack_reports_no_evidence")
        if quality.score < self.minimum_quality_score:
            reasons.append("evidence_quality_below_threshold")
        if pack.assessment.coverage < self.minimum_pack_coverage:
            reasons.append("retriever_coverage_below_threshold")
        if quality.qualifying_evidence_count == 0:
            reasons.append("no_qualifying_evidence")
        if quality.excluded_injection_count > 0:
            reasons.append("evidence_excluded_for_prompt_injection_risk")
        answerable = not pack.assessment.no_evidence and quality.score >= self.minimum_quality_score and quality.qualifying_evidence_count > 0
        # Contradictions do not always make the question unanswerable, but final assertive generation must acknowledge them.
        score = min(pack.assessment.confidence, quality.score)
        requires_human = bool(quality.unresolved_material_contradictions) or quality.excluded_injection_count > 0
        requires_repair = not answerable and not requires_human
        return AnswerabilityAssessment(
            answerable=answerable,
            score=round(max(0.0, min(1.0, score)), 5),
            reasons=tuple(dict.fromkeys(reasons)),
            requires_repair=requires_repair,
            requires_human_review=requires_human,
        )
