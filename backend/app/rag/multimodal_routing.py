from __future__ import annotations

import re

from app.domain.multimodal_rag import EvidenceModality, MultimodalIntent, MultimodalRoute
from app.domain.orchestration import AgentName


class MultimodalRouter:
    version = "multimodal-router-v1"

    _AGENT_MODALITIES = {
        AgentName.HOSPITAL_VERIFICATION: {EvidenceModality.FHIR, EvidenceModality.DOCUMENT, EvidenceModality.IMAGE, EvidenceModality.TABLE},
        AgentName.INVOICE_VERIFICATION: {EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.FHIR},
        AgentName.CODING: {EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.FHIR},
        AgentName.EVIDENCE_FUSION: set(EvidenceModality),
        AgentName.CRITIC: set(EvidenceModality),
        AgentName.DECISION_SUPPORT: set(EvidenceModality),
        AgentName.FRAUD_WASTE: {EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.AUDIO, EvidenceModality.VIDEO, EvidenceModality.FHIR},
    }

    def plan(
        self,
        query: str,
        *,
        requested_modalities: tuple[EvidenceModality, ...] = (),
        required_modalities: tuple[EvidenceModality, ...] = (),
        agent: AgentName | None = None,
    ) -> MultimodalRoute:
        q = query.lower()
        inferred: set[EvidenceModality] = {EvidenceModality.TEXT, EvidenceModality.DOCUMENT}
        reasons: list[str] = ["textual evidence baseline"]
        intent = MultimodalIntent.GENERAL_EVIDENCE

        if re.search(r"\b(invoice|bill|receipt|table|line item|amount)\b", q):
            inferred |= {EvidenceModality.TABLE, EvidenceModality.IMAGE}
            intent = MultimodalIntent.INVOICE_VERIFICATION
            reasons.append("invoice/table terms")
        if re.search(r"\b(image|photo|scan|picture|visual|screenshot|bbox)\b", q):
            inferred.add(EvidenceModality.IMAGE)
            intent = MultimodalIntent.DOCUMENT_VISUAL
            reasons.append("visual evidence terms")
        if re.search(r"\b(audio|call|recording|transcript|speaker|said)\b", q):
            inferred.add(EvidenceModality.AUDIO)
            intent = MultimodalIntent.AUDIO_VERIFICATION
            reasons.append("audio terms")
        if re.search(r"\b(video|keyframe|frame|footage|timeline|timecode)\b", q):
            inferred.add(EvidenceModality.VIDEO)
            intent = MultimodalIntent.VIDEO_TIMELINE
            reasons.append("video/timeline terms")
        if re.search(r"\b(fhir|hospital|eob|encounter|coverage|clinical record)\b", q):
            inferred.add(EvidenceModality.FHIR)
            intent = MultimodalIntent.FHIR_CROSS_CHECK
            reasons.append("FHIR/hospital terms")
        if re.search(r"\b(compare|cross[- ]?check|mismatch|inconsisten|contradict|verify across)\b", q):
            intent = MultimodalIntent.CROSS_MODAL_VERIFICATION
            inferred |= {EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.FHIR}
            reasons.append("cross-modal verification terms")

        allowed = self._AGENT_MODALITIES.get(agent, set(EvidenceModality))
        if requested_modalities:
            # Caller selection may narrow the router but never expands the agent profile.
            selected = set(requested_modalities) & allowed
        else:
            selected = inferred & allowed
        selected |= set(required_modalities) & allowed
        if not selected:
            selected = {EvidenceModality.TEXT} & allowed or set(allowed)

        required = tuple(sorted(set(required_modalities) & selected, key=lambda x: x.value))
        return MultimodalRoute(
            intent=intent,
            modalities=tuple(sorted(selected, key=lambda x: x.value)),
            required_modalities=required,
            agent=agent,
            reasons=tuple(reasons),
            planner_version=self.version,
        )
