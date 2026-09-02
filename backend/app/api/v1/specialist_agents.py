from fastapi import APIRouter

from app.schemas.specialist_agents import SpecialistAgentModelResponse
from app.services.specialist_agents import specialist_agent_model_contract

router = APIRouter(tags=["specialist-agents"])


@router.get("/specialist-agent-model", response_model=SpecialistAgentModelResponse)
def specialist_model() -> SpecialistAgentModelResponse:
    return SpecialistAgentModelResponse(**specialist_agent_model_contract())
