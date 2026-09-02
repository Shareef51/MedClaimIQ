from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.multimodal_rag import EvidenceModality
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain


class MultimodalAgentEscalation(StrEnum):
    MATERIAL_CONFLICT = "multimodal_conflict"
    MISSING_REQUIRED_MODALITY = "missing_required_modality"
    INSUFFICIENT_MULTIMODAL_EVIDENCE = "insufficient_multimodal_evidence"


@dataclass(frozen=True, slots=True)
class MultimodalAgentProfile:
    agent: AgentName
    allowed_modalities: tuple[EvidenceModality, ...]
    default_required_modalities: tuple[EvidenceModality, ...]
    domains: tuple[RAGDomain, ...]
    query_template: str
    max_items: int = 12
    profile_version: str = "multimodal-agent-profile-v1"

    def clamp_modalities(
        self,
        requested: tuple[EvidenceModality, ...] = (),
        required: tuple[EvidenceModality, ...] = (),
    ) -> tuple[tuple[EvidenceModality, ...], tuple[EvidenceModality, ...]]:
        allowed=set(self.allowed_modalities)
        selected=tuple(m for m in (requested or self.allowed_modalities) if m in allowed)
        if not selected:
            selected=self.allowed_modalities
        required_candidates=required or self.default_required_modalities
        required_selected=tuple(m for m in required_candidates if m in set(selected) and m in allowed)
        # A caller cannot use an explicit request to silently drop profile-required modalities.
        for modality in self.default_required_modalities:
            if modality in allowed and modality not in selected:
                selected=selected+(modality,)
            if modality in selected and modality not in required_selected:
                required_selected=required_selected+(modality,)
        return tuple(dict.fromkeys(selected)), tuple(dict.fromkeys(required_selected))


MULTIMODAL_AGENT_PROFILES: dict[AgentName, MultimodalAgentProfile] = {
    AgentName.HOSPITAL_VERIFICATION: MultimodalAgentProfile(
        agent=AgentName.HOSPITAL_VERIFICATION,
        allowed_modalities=(EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.FHIR),
        default_required_modalities=(EvidenceModality.FHIR,),
        domains=(RAGDomain.HOSPITAL, RAGDomain.CLAIM, RAGDomain.EVIDENCE),
        query_template="Cross-verify hospital/FHIR records, submitted claim evidence, service dates, codes and billed amounts for this claim.",
    ),
    AgentName.INVOICE_VERIFICATION: MultimodalAgentProfile(
        agent=AgentName.INVOICE_VERIFICATION,
        allowed_modalities=(EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.FHIR),
        default_required_modalities=(EvidenceModality.TABLE,),
        domains=(RAGDomain.INVOICE, RAGDomain.CLAIM, RAGDomain.HOSPITAL, RAGDomain.EVIDENCE),
        query_template="Verify invoice totals, line items, dates, codes and provider evidence across document/table/image/FHIR sources.",
    ),
    AgentName.FRAUD_WASTE: MultimodalAgentProfile(
        agent=AgentName.FRAUD_WASTE,
        allowed_modalities=(EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE, EvidenceModality.AUDIO, EvidenceModality.VIDEO, EvidenceModality.FHIR),
        default_required_modalities=(),
        domains=(RAGDomain.CLAIM, RAGDomain.INVOICE, RAGDomain.HOSPITAL, RAGDomain.HISTORICAL_CLAIMS, RAGDomain.EVIDENCE),
        query_template="Surface evidence-backed cross-modal fraud/waste risk signals without accusing any person or provider.",
    ),
    AgentName.EVIDENCE_FUSION: MultimodalAgentProfile(
        agent=AgentName.EVIDENCE_FUSION,
        allowed_modalities=tuple(EvidenceModality),
        default_required_modalities=(),
        domains=tuple(RAGDomain),
        query_template="Fuse authoritative claim evidence across all available modalities while preserving conflicts and citations.",
        max_items=18,
    ),
    AgentName.CRITIC: MultimodalAgentProfile(
        agent=AgentName.CRITIC,
        allowed_modalities=tuple(EvidenceModality),
        default_required_modalities=(),
        domains=tuple(RAGDomain),
        query_template="Critically verify specialist findings against cross-modal evidence, citations, contradictions and missing modalities.",
        max_items=18,
    ),
    AgentName.DECISION_SUPPORT: MultimodalAgentProfile(
        agent=AgentName.DECISION_SUPPORT,
        allowed_modalities=tuple(EvidenceModality),
        default_required_modalities=(),
        domains=tuple(RAGDomain),
        query_template="Collect the strongest cited cross-modal evidence needed for advisory decision support; preserve uncertainty and conflicts.",
        max_items=18,
    ),
}

MULTIMODAL_ORCHESTRATED_AGENTS=frozenset(MULTIMODAL_AGENT_PROFILES)


def multimodal_agent_orchestration_contract() -> dict[str, object]:
    return {
        "architecture": "langgraph-multimodal-specialist-orchestration",
        "multimodal_agents": [a.value for a in sorted(MULTIMODAL_ORCHESTRATED_AGENTS, key=lambda x:x.value)],
        "parallel_multimodal_agents": [AgentName.HOSPITAL_VERIFICATION.value, AgentName.INVOICE_VERIFICATION.value, AgentName.FRAUD_WASTE.value],
        "sequential_multimodal_agents": [AgentName.EVIDENCE_FUSION.value, AgentName.CRITIC.value, AgentName.DECISION_SUPPORT.value],
        "agent_request_boundary": "profile-clamped requested/required modalities and domain scope",
        "escalations": [e.value for e in MultimodalAgentEscalation],
        "human_checkpoint": "durable LangGraph interrupt with persisted checkpoint reason",
        "citation_contract": "multimodal findings preserve item evidence keys plus exact page/bbox/timecode/frame/FHIR anchors",
        "safety_invariants": [
            "agents cannot broaden tenant/claim/ACL or Release 30 governed knowledge scope",
            "multimodal retrieval is read-only and bounded per specialist profile",
            "material cross-modal inconsistency deterministically requires human review",
            "missing required modality deterministically requires human review",
            "shadow/generated visual descriptions remain retrieval aids rather than authoritative facts",
            "no agent can finalize, approve, deny, pay, diagnose or treat a claim",
        ],
    }
