from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read
from app.db.session import get_db
from app.core.config import get_settings
from app.domain.appeal_reconsideration import appeal_reconsideration_contract
from app.schemas.appeal_reconsideration import (
    AppealAgentRunRequest, AppealAnnotationRequest, AppealCheckpointResumeRequest,
    AppealEscalationRequest, AppealMissingEvidenceRequest, AppealRAGSearchRequest,
    AppealReingestRequest, AppealSnapshotBuildRequest,
)
from app.services.appeal_reconsideration import AppealReconsiderationService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router=APIRouter(tags=["appeal-evidence-reconsideration"])


def _identity(request:Request):
    identity=getattr(request.state,"identity",None)
    if identity is None: raise HTTPException(401,"authenticated identity is unavailable")
    return identity


def _service(request:Request,db:Session,identity,*,use_embedder:bool=False)->AppealReconsiderationService:
    settings=get_settings();embedder=None
    if use_embedder:
        embedder=request.app.state.rag_embedder_provider()
    return AppealReconsiderationService(
        db,identity.principal.tenant_id,embedder=embedder,
        embedding_model=settings.rag_embedding_model,embedding_dimensions=settings.rag_embedding_dimensions,index_version=settings.rag_index_version,
    )


def _handle(exc:Exception):
    if isinstance(exc,LookupError): raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)): raise HTTPException(409,str(exc)) from exc
    if isinstance(exc,(ValueError,PermissionError)): raise HTTPException(400,str(exc)) from exc
    raise exc


@router.get("/appeal-reconsideration-model")
def model(): return appeal_reconsideration_contract()


@router.get("/claims/{claim_id}/appeals/{appeal_id}/reconsideration")
def workbench(claim_id:str,appeal_id:str,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id)
    try:return _service(request,db,identity).snapshot_view(claim_id,appeal_id)
    except Exception as exc:_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/reingest")
def reingest(claim_id:str,appeal_id:str,payload:AppealReingestRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        svc.authorize_independent_reviewer(claim_id,appeal_id,identity.principal.user_id)
        row=svc.process_reingestion(claim_id,appeal_id,payload.evidence_id,trace_id=getattr(request.state,"trace_id",None));db.commit()
        return {"reingestion_id":row.reingestion_id,"status":row.status,"modality":row.modality,"chunk_count":row.chunk_count,"file_validation_status":row.file_validation_status,"malware_verdict":row.malware_verdict,"embedding_model":row.embedding_model,"index_version":row.index_version}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/snapshot")
def build_snapshot(claim_id:str,appeal_id:str,payload:AppealSnapshotBuildRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        svc.authorize_independent_reviewer(claim_id,appeal_id,identity.principal.user_id)
        row=svc.build_snapshot(claim_id,appeal_id,identity.principal.user_id,"human",trace_id=getattr(request.state,"trace_id",None));db.commit()
        return {"snapshot_id":row.snapshot_id,"snapshot_version":row.snapshot_version,"snapshot_sha256":row.snapshot_sha256,"status":row.status,"modalities":row.modalities,"source_count":row.source_count}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/search")
def search(claim_id:str,appeal_id:str,payload:AppealRAGSearchRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity,use_embedder=True)
    try:
        svc.authorize_independent_reviewer(claim_id,appeal_id,identity.principal.user_id)
        result=svc.search(claim_id,appeal_id,payload.query,limit=payload.top_k,trace_id=getattr(request.state,"trace_id",None));db.commit()
        return {"run_id":result["run"].run_id,"snapshot_id":result["snapshot"].snapshot_id,"strategy":result["run"].strategy,"pack_sha256":result["run"].pack_sha256,"items":[{"item_id":x.item_id,"source_scope":x.source_scope,"source_id":x.source_id,"source_version":x.source_version,"modality":x.modality,"rank":x.rank,"score":x.score,"text_preview":x.text_preview,"citation":x.citation,"retrieval_sources":x.retrieval_sources} for x in result["items"]],"comparisons":[{"comparison_id":x.comparison_id,"comparison_type":x.comparison_type,"field":x.field,"severity":x.severity,"confidence":x.confidence,"description":x.description,"citations":x.citations} for x in result["comparisons"]]}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/agent-run")
def agent_run(claim_id:str,appeal_id:str,payload:AppealAgentRunRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity,use_embedder=True)
    try:
        svc.authorize_independent_reviewer(claim_id,appeal_id,identity.principal.user_id)
        row=svc.run_reconsideration_agent(claim_id,appeal_id,query=payload.query,trace_id=getattr(request.state,"trace_id",None),idempotency_key=payload.idempotency_key);db.commit()
        return {"reconsideration_run_id":row.reconsideration_run_id,"recommendation":row.recommendation,"confidence":row.confidence,"recommendation_summary":row.recommendation_summary,"evidence_refs":row.evidence_refs,"changed_fact_refs":row.changed_fact_refs,"contradiction_refs":row.contradiction_refs,"missing_evidence_requests":row.missing_evidence_requests,"escalation_reasons":row.escalation_reasons,"requires_human_review":row.requires_human_review,"adjudication_authority":row.adjudication_authority}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/annotations")
def annotate(claim_id:str,appeal_id:str,payload:AppealAnnotationRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        row=svc.add_annotation(claim_id,appeal_id,identity.principal.user_id,target_type=payload.target_type,target_id=payload.target_id,body=payload.body,anchor=payload.anchor,tags=payload.tags,idempotency_key=payload.idempotency_key);db.commit();return {"annotation_id":row.annotation_id,"created_at":row.created_at}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/missing-evidence")
def missing_evidence(claim_id:str,appeal_id:str,payload:AppealMissingEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        row=svc.request_missing_evidence(claim_id,appeal_id,identity.principal.user_id,document_types=payload.document_types,rationale=payload.rationale,idempotency_key=payload.idempotency_key);db.commit();return {"request_id":row.request_id,"status":row.status,"created_at":row.created_at}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/escalate")
def escalate(claim_id:str,appeal_id:str,payload:AppealEscalationRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        row=svc.escalate(claim_id,appeal_id,identity.principal.user_id,reason=payload.reason,assigned_queue=payload.assigned_queue,idempotency_key=payload.idempotency_key);db.commit();return {"escalation_id":row.escalation_id,"level":row.level,"assigned_queue":row.assigned_queue,"status":row.status}
    except Exception as exc:db.rollback();_handle(exc)


@router.post("/claims/{claim_id}/appeals/{appeal_id}/reconsideration/checkpoints/{checkpoint_id}/resume")
def resume_checkpoint(claim_id:str,appeal_id:str,checkpoint_id:str,payload:AppealCheckpointResumeRequest,request:Request,db:Session=Depends(get_db)):
    identity=_identity(request);_authorize_claim_read(db,identity,claim_id);svc=_service(request,db,identity)
    try:
        row=svc.resume_checkpoint(claim_id,appeal_id,checkpoint_id,identity.principal.user_id);db.commit();return {"checkpoint_id":row.checkpoint_id,"status":row.status,"resumed_by_user_id":row.resumed_by_user_id,"resumed_at":row.resumed_at}
    except Exception as exc:db.rollback();_handle(exc)
