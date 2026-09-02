from __future__ import annotations

import re
from collections import defaultdict

from app.domain.multimodal_rag import EvidenceModality, MultimodalCandidate

_TOKEN = re.compile(r"[a-z0-9]{2,}", re.I)


def _overlap(query: str, text: str) -> float:
    q = set(_TOKEN.findall(query.lower()))
    if not q:
        return 0.0
    t = set(_TOKEN.findall(text.lower()))
    return len(q & t) / len(q)


class ModalityAwareReranker:
    version = "multimodal-reranker-v1"

    _BOOST = {
        EvidenceModality.FHIR: 0.10,
        EvidenceModality.TABLE: 0.08,
        EvidenceModality.IMAGE: 0.06,
        EvidenceModality.AUDIO: 0.04,
        EvidenceModality.VIDEO: 0.04,
        EvidenceModality.DOCUMENT: 0.03,
        EvidenceModality.TEXT: 0.02,
    }

    def rerank(self, query: str, candidates: list[MultimodalCandidate], *, limit: int) -> list[MultimodalCandidate]:
        scored: list[tuple[float, MultimodalCandidate]] = []
        for item in candidates:
            valid, _ = item.citation.validate()
            score = (
                0.42 * max(0.0, min(1.0, item.score))
                + 0.24 * max(0.0, min(1.0, item.confidence))
                + 0.14 * max(0.0, min(1.0, item.authority_rank / 100.0))
                + 0.14 * _overlap(query, item.text)
                + (0.04 if valid else -0.20)
                + self._BOOST.get(item.modality, 0.0)
            )
            scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].item_id))

        # First pass guarantees modality diversity before filling remaining slots.
        selected: list[MultimodalCandidate] = []
        seen: set[EvidenceModality] = set()
        by_modality: dict[EvidenceModality, list[tuple[float, MultimodalCandidate]]] = defaultdict(list)
        for pair in scored:
            by_modality[pair[1].modality].append(pair)
        for modality in sorted(by_modality, key=lambda x: x.value):
            if len(selected) >= limit:
                break
            score, item = by_modality[modality][0]
            selected.append(self._with_score(item, score))
            seen.add(modality)
        used = {x.item_id for x in selected}
        for score, item in scored:
            if len(selected) >= limit:
                break
            if item.item_id in used:
                continue
            selected.append(self._with_score(item, score))
            used.add(item.item_id)
        selected.sort(key=lambda x: (-x.score, x.item_id))
        return selected

    @staticmethod
    def _with_score(item: MultimodalCandidate, score: float) -> MultimodalCandidate:
        return MultimodalCandidate(
            item_id=item.item_id,
            modality=item.modality,
            domain=item.domain,
            source_id=item.source_id,
            source_version=item.source_version,
            text=item.text,
            score=round(max(0.0, min(1.0, score)), 6),
            confidence=item.confidence,
            authority_rank=item.authority_rank,
            citation=item.citation,
            metadata=item.metadata,
            retrieval_sources=item.retrieval_sources,
        )
