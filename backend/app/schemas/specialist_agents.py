from __future__ import annotations

from pydantic import BaseModel


class SpecialistAgentModelResponse(BaseModel):
    agents: list[str]
    prompt_versioning: dict[str, object]
    structured_outputs: dict[str, object]
    evidence_boundary: dict[str, object]
    tool_policy: dict[str, object]
    confidence_contracts: dict[str, object]
    retry_fallback: dict[str, object]
    safety_boundaries: list[str]
