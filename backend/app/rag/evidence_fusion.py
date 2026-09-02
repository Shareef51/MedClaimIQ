from __future__ import annotations

import uuid
from collections import Counter

from app.domain.cross_source_rag import (
    ContradictionSummary, EvidenceItem, EvidencePack, EvidencePackAssessment, RetrieverKind, deduplicate_evidence,
)


class CrossSourceEvidenceFusion:
    def fuse(
        self,
        *,
        claim_id: str,
        query: str,
        items: tuple[EvidenceItem, ...],
        contradictions: tuple[ContradictionSummary, ...],
        planned_retrievers: tuple[RetrieverKind, ...],
        executed_retrievers: tuple[RetrieverKind, ...],
        planner_version: str,
        limit: int = 20,
    ) -> EvidencePack:
        unique = list(deduplicate_evidence(items))
        unique.sort(key=lambda item: (item.authority_rank, item.confidence), reverse=True)
        selected = tuple(unique[:limit])
        available = {item.retriever for item in selected}
        expected = set(planned_retrievers)
        coverage = len(available & expected) / max(1, len(expected))
        source_types = {item.source_type for item in selected}
        diversity = min(1.0, len(source_types) / max(1, min(4, len(selected)))) if selected else 0.0
        weighted = [item.confidence * (item.authority_rank / 100.0) for item in selected]
        confidence = sum(weighted) / len(weighted) if weighted else 0.0
        material = sum(1 for item in contradictions if item.severity == "material" and item.status == "open")
        if material:
            confidence *= max(0.35, 1.0 - min(0.5, material * 0.12))
        no_evidence = not selected or confidence < 0.20
        reasons: list[str] = []
        if not selected:
            reasons.append("no_cross_source_evidence")
        if coverage < 0.5:
            reasons.append("limited_retriever_coverage")
        if material:
            reasons.append("unresolved_material_contradictions")
        return EvidencePack(
            pack_id=f"epack_{uuid.uuid4().hex}", claim_id=claim_id, query=query, items=selected,
            contradictions=contradictions,
            assessment=EvidencePackAssessment(
                confidence=round(max(0.0, min(1.0, confidence)), 5), coverage=round(coverage, 5),
                source_diversity=round(diversity, 5), no_evidence=no_evidence,
                unresolved_material_contradictions=material, reasons=tuple(reasons),
            ),
            executed_retrievers=executed_retrievers, planner_version=planner_version,
        )
