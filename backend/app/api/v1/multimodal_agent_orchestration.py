from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.v1.multimodal_rag import _identity
from app.api.v1.rag import _authorize_claim_read
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.domain.multimodal_agent_orchestration import MULTIMODAL_AGENT_PROFILES, multimodal_agent_orchestration_contract
from app.repositories.multimodal_agent_orchestration import MultimodalAgentOrchestrationRepository
from app.repositories.orchestration import OrchestrationRepository
from app.schemas.multimodal_agent_orchestration import MultimodalAgentInvestigationSummary, MultimodalAgentProfileRequest, MultimodalAgentProfileResponse

router=APIRouter(tags=["multimodal-agent-orchestration"])

@router.get("/multimodal-agent-orchestration-model")
def model_contract(): return multimodal_agent_orchestration_contract()

@router.post("/claims/{claim_id}/agent-workflows/multimodal-profile",response_model=MultimodalAgentProfileResponse)
def profile_plan(claim_id:str,payload:MultimodalAgentProfileRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    if Permission.CLAIM_VIEW_AI_FINDINGS not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403,detail="AI findings permission is required")
    profile=MULTIMODAL_AGENT_PROFILES.get(payload.agent)
    if profile is None: raise HTTPException(status_code=422,detail="agent does not have a multimodal orchestration profile")
    selected,required=profile.clamp_modalities(payload.requested_modalities,payload.required_modalities)
    return MultimodalAgentProfileResponse(agent=payload.agent,allowed_modalities=list(profile.allowed_modalities),effective_modalities=list(selected),effective_required_modalities=list(required),domains=[x.value for x in profile.domains],max_items=profile.max_items,profile_version=profile.profile_version)

@router.get("/claims/{claim_id}/agent-workflows/{workflow_id}/multimodal-investigations",response_model=list[MultimodalAgentInvestigationSummary])
def investigations(claim_id:str,workflow_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request); _authorize_claim_read(db,identity,claim_id)
    if Permission.CLAIM_VIEW_AI_FINDINGS not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403,detail="AI findings permission is required")
    workflow=OrchestrationRepository(db,identity.principal.tenant_id).get_workflow(workflow_id)
    if workflow is None or workflow.claim_id!=claim_id: raise HTTPException(status_code=404,detail="workflow not found")
    rows=MultimodalAgentOrchestrationRepository(db,identity.principal.tenant_id).workflow_investigations(workflow_id)
    return [MultimodalAgentInvestigationSummary(investigation_id=x.investigation_id,agent=x.agent_name,attempt=x.attempt,pack_id=x.pack_id,answerability=x.answerability,confidence=x.confidence,requested_modalities=list(x.requested_modalities),required_modalities=list(x.required_modalities),material_inconsistency_count=x.material_inconsistency_count,blocking_gap_count=x.blocking_gap_count,human_review_required=x.human_review_required,escalation_reasons=list(x.escalation_reasons),created_at=x.created_at) for x in rows]
