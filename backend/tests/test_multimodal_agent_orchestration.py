from app.domain.multimodal_agent_orchestration import MULTIMODAL_AGENT_PROFILES, MultimodalAgentEscalation, multimodal_agent_orchestration_contract
from app.domain.multimodal_rag import EvidenceModality
from app.domain.orchestration import AgentName, HumanCheckpointReason
from app.services.multimodal_agent_orchestration import deterministic_multimodal_review_finding
from app.agents.multimodal_context import MultimodalAgentContext, MultimodalAgentEvidenceItem
from app.domain.advanced_rag import Answerability

def test_multimodal_agents_are_exact_six():
    expected={AgentName.HOSPITAL_VERIFICATION,AgentName.INVOICE_VERIFICATION,AgentName.FRAUD_WASTE,AgentName.EVIDENCE_FUSION,AgentName.CRITIC,AgentName.DECISION_SUPPORT}
    assert set(MULTIMODAL_AGENT_PROFILES)==expected

def test_hospital_profile_cannot_drop_required_fhir():
    p=MULTIMODAL_AGENT_PROFILES[AgentName.HOSPITAL_VERIFICATION]
    selected,required=p.clamp_modalities((EvidenceModality.DOCUMENT,),())
    assert EvidenceModality.FHIR in selected and EvidenceModality.FHIR in required

def test_invoice_requires_table():
    _,required=MULTIMODAL_AGENT_PROFILES[AgentName.INVOICE_VERIFICATION].clamp_modalities()
    assert EvidenceModality.TABLE in required

def test_deterministic_review_finding_preserves_citation():
    item=MultimodalAgentEvidenceItem("mm:x","x",EvidenceModality.VIDEO,"frame evidence","vid","v1",80,0.9,{"start_ms":1000,"frame_index":3,"frame_sha256":"a"*64})
    ctx=MultimodalAgentContext("inv","critic","pack","run","b"*64,Answerability.INSUFFICIENT,0.6,(),(item,),human_review_required=True,escalation_reasons=(MultimodalAgentEscalation.MATERIAL_CONFLICT.value,))
    f=deterministic_multimodal_review_finding(AgentName.CRITIC,ctx)
    assert f and f.requires_human_review and f.evidence_keys==("mm:x",)
    assert f.metadata["multimodal_citations"]["mm:x"]["frame_index"]==3

def test_checkpoint_reasons_exist():
    assert HumanCheckpointReason.MULTIMODAL_CONFLICT.value=="multimodal_conflict"
    assert HumanCheckpointReason.MISSING_REQUIRED_MODALITY.value=="missing_required_modality"

def test_contract_declares_parallel_and_safety():
    c=multimodal_agent_orchestration_contract()
    assert set(c["parallel_multimodal_agents"])=={"hospital_verification","invoice_verification","fraud_waste"}
    assert any("finalize" in x for x in c["safety_invariants"])
