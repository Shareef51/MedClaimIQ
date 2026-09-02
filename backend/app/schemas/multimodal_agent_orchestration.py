from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.domain.multimodal_rag import EvidenceModality
from app.domain.orchestration import AgentName

class MultimodalAgentProfileRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    agent: AgentName
    requested_modalities: tuple[EvidenceModality,...]=()
    required_modalities: tuple[EvidenceModality,...]=()

class MultimodalAgentProfileResponse(BaseModel):
    agent: AgentName
    allowed_modalities: list[EvidenceModality]
    effective_modalities: list[EvidenceModality]
    effective_required_modalities: list[EvidenceModality]
    domains: list[str]
    max_items: int
    profile_version: str

class MultimodalAgentInvestigationSummary(BaseModel):
    investigation_id: str
    agent: AgentName
    attempt: int
    pack_id: str
    answerability: str
    confidence: float
    requested_modalities: list[str]
    required_modalities: list[str]
    material_inconsistency_count: int
    blocking_gap_count: int
    human_review_required: bool
    escalation_reasons: list[str]
    created_at: datetime
