from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.schemas.orchestration import WorkflowExecuteResponse, WorkflowModelResponse, WorkflowResponse, WorkflowResumeRequest, WorkflowStartRequest
from app.services.orchestration import OrchestrationInvariantError, OrchestrationService, orchestration_model_contract
from app.repositories.orchestration import OrchestrationRepository
from app.models.orchestration import AgentHumanCheckpointModel
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.orchestration.streaming import WorkflowEventStreamer
from sqlalchemy import select

router = APIRouter(tags=["agent-orchestration"])


@router.get("/agent-orchestration-model", response_model=WorkflowModelResponse)
def model_contract() -> WorkflowModelResponse:
    return WorkflowModelResponse(**orchestration_model_contract())


def _response(model, checkpoint_id: str | None = None) -> WorkflowResponse:
    return WorkflowResponse(
        workflow_id=model.workflow_id, claim_id=model.claim_id, thread_id=model.thread_id,
        status=model.status, evidence_pack_id=model.evidence_pack_id,
        selected_agents=list(model.selected_agents), completed_agents=list(model.completed_agents),
        failed_agents=list(model.failed_agents), state_version=model.state_version, checkpoint_id=checkpoint_id,
    )


@router.post("/claims/{claim_id}/agent-workflows", response_model=WorkflowResponse)
def start_workflow(claim_id: str, payload: WorkflowStartRequest, request: Request, db: Session = Depends(get_db)) -> WorkflowResponse:
    identity = _identity(request)
    _authorize_claim_read(db, identity, claim_id)
    try:
        service = OrchestrationService(db, identity.principal.tenant_id)
        model = service.start(claim_id=claim_id, user_id=identity.principal.user_id, payload=payload, trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"))
        db.commit()
        checkpoint = db.scalar(select(AgentHumanCheckpointModel).where(
            AgentHumanCheckpointModel.tenant_id == identity.principal.tenant_id,
            AgentHumanCheckpointModel.workflow_id == model.workflow_id,
            AgentHumanCheckpointModel.status == "waiting",
        ))
        return _response(model, checkpoint.checkpoint_id if checkpoint else None)
    except OrchestrationInvariantError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/agent-workflows/{workflow_id}/resume", response_model=WorkflowResponse)
def resume_workflow(claim_id: str, workflow_id: str, payload: WorkflowResumeRequest, request: Request, db: Session = Depends(get_db)) -> WorkflowResponse:
    identity = _identity(request)
    _authorize_claim_read(db, identity, claim_id)
    try:
        model = OrchestrationService(db, identity.principal.tenant_id).resume(
            workflow_id=workflow_id, reviewer_user_id=identity.principal.user_id,
            reviewer_role=identity.principal.role, payload=payload, trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
        )
        if model.claim_id != claim_id:
            raise OrchestrationInvariantError("workflow is not bound to requested claim")
        db.commit()
        if payload.action == "continue":
            result = request.app.state.agent_workflow_runner_provider().resume_graph(
                tenant_id=identity.principal.tenant_id, claim_id=claim_id, workflow_id=workflow_id,
                reviewer_payload={
                    "checkpoint_id": payload.checkpoint_id, "action": payload.action,
                    "reviewer_user_id": identity.principal.user_id, "comment": payload.comment,
                },
                trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
            )
            model = OrchestrationRepository(db, identity.principal.tenant_id).get_workflow(workflow_id) or model
            return _response(model, result.checkpoint_id)
        return _response(model)
    except OrchestrationInvariantError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc


def _require_claim_reviewer(identity) -> None:
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403, detail="claim review permission is required to execute agent workflows")


@router.post("/claims/{claim_id}/agent-workflows/{workflow_id}/execute", response_model=WorkflowExecuteResponse)
def execute_workflow(
    claim_id: str, workflow_id: str, request: Request, db: Session = Depends(get_db),
) -> WorkflowExecuteResponse:
    identity = _identity(request)
    _authorize_claim_read(db, identity, claim_id)
    _require_claim_reviewer(identity)
    try:
        result = request.app.state.agent_workflow_runner_provider().execute(
            tenant_id=identity.principal.tenant_id, claim_id=claim_id, workflow_id=workflow_id,
            trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
        )
        model = OrchestrationRepository(db, identity.principal.tenant_id).get_workflow(workflow_id)
        if model is None:
            raise OrchestrationInvariantError("workflow disappeared after execution")
        return WorkflowExecuteResponse(
            workflow_id=workflow_id, claim_id=claim_id, status=result.status,
            checkpoint_id=result.checkpoint_id, thread_id=model.thread_id, state_version=model.state_version,
        )
    except OrchestrationInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/claims/{claim_id}/agent-workflows/{workflow_id}/events")
def stream_workflow_events(
    claim_id: str, workflow_id: str, request: Request, after_sequence: int = 0, db: Session = Depends(get_db),
):
    identity = _identity(request)
    _authorize_claim_read(db, identity, claim_id)
    workflow = OrchestrationRepository(db, identity.principal.tenant_id).get_workflow(workflow_id)
    if workflow is None or workflow.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="workflow was not found")
    session_factory = request.app.state.session_factory_provider()
    streamer = WorkflowEventStreamer(
        session_factory=session_factory, tenant_id=identity.principal.tenant_id, workflow_id=workflow_id,
        after_sequence=after_sequence,
    )
    return StreamingResponse(
        streamer.events(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
