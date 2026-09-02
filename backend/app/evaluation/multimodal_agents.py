from __future__ import annotations
from app.domain.multimodal_agent_orchestration import MULTIMODAL_AGENT_PROFILES, MultimodalAgentEscalation
from app.domain.multimodal_rag import EvidenceModality
from app.domain.orchestration import AgentName

def evaluate_multimodal_agent_contracts() -> dict[str,object]:
    checks=[]
    for agent,profile in MULTIMODAL_AGENT_PROFILES.items():
        selected,required=profile.clamp_modalities()
        checks.append(bool(selected) and set(required).issubset(set(selected)) and set(selected).issubset(set(profile.allowed_modalities)))
    checks += [
        EvidenceModality.FHIR in MULTIMODAL_AGENT_PROFILES[AgentName.HOSPITAL_VERIFICATION].default_required_modalities,
        EvidenceModality.TABLE in MULTIMODAL_AGENT_PROFILES[AgentName.INVOICE_VERIFICATION].default_required_modalities,
        MultimodalAgentEscalation.MATERIAL_CONFLICT.value=="multimodal_conflict",
        MultimodalAgentEscalation.MISSING_REQUIRED_MODALITY.value=="missing_required_modality",
    ]
    return {"metric":"multimodal_agent_contract_accuracy","value":sum(checks)/len(checks),"passed":all(checks),"checks":len(checks)}
