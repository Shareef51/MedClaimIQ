from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read, _identity
from app.api.v1.review_workbench import _handle, _require
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import Permission
from app.domain.multimodal_review import multimodal_reviewer_contract
from app.schemas.multimodal_review import EvidenceAccessResponse, MultimodalReviewAnnotationCreate, MultimodalReviewAnnotationResponse
from app.services.multimodal_review import MultimodalReviewService

router=APIRouter(tags=["multimodal-reviewer-workbench"])


def _reviewer(request: Request):
    identity=_identity(request); _require(identity, Permission.CLAIM_REVIEW); return identity


@router.get("/multimodal-review-model")
def model():
    return multimodal_reviewer_contract()


@router.get("/claims/{claim_id}/review/multimodal")
def snapshot(claim_id: str, request: Request, db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    return MultimodalReviewService(db, identity.principal.tenant_id).snapshot(claim_id)


@router.post("/claims/{claim_id}/review/multimodal/annotations", response_model=MultimodalReviewAnnotationResponse)
def add_annotation(claim_id: str, payload: MultimodalReviewAnnotationCreate, request: Request, x_review_lock_token: str=Header(alias="X-Review-Lock-Token"), db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    try:
        row=MultimodalReviewService(db, identity.principal.tenant_id).add_annotation(
            claim_id, identity.principal.user_id, x_review_lock_token,
            target_type=payload.target_type.value, target_id=payload.target_id,
            annotation_kind=payload.annotation_kind.value, anchor=payload.anchor, body=payload.body,
            tags=payload.tags, idempotency_key=payload.idempotency_key, trace_id=getattr(identity,"trace_id",None),
        )
        db.commit(); return row
    except Exception as exc:
        db.rollback(); _handle(exc)


@router.get("/claims/{claim_id}/review/evidence/{evidence_id}/access", response_model=EvidenceAccessResponse)
def evidence_access(claim_id: str, evidence_id: str, request: Request, db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    settings=get_settings()
    try:
        storage=request.app.state.object_storage_provider()
        return MultimodalReviewService(db, identity.principal.tenant_id).evidence_access(
            claim_id, evidence_id, storage=storage, bucket_name=settings.s3_bucket, expires_seconds=300,
        )
    except Exception as exc:
        _handle(exc)


@router.get("/claims/{claim_id}/review/evidence/{evidence_id}/page-preview")
def evidence_page_preview(claim_id: str, evidence_id: str, request: Request, page_number: int=Query(default=1, ge=1, le=10000), bbox: str | None=None, db: Session=Depends(get_db)):
    identity=_reviewer(request); _authorize_claim_read(db, identity, claim_id)
    settings=get_settings()
    parsed_bbox=None
    if bbox:
        try:
            parsed_bbox=[float(x) for x in bbox.split(",")]
            if len(parsed_bbox)!=4: raise ValueError()
        except ValueError as exc:
            raise HTTPException(status_code=422,detail="bbox must contain four comma-separated numbers") from exc
    try:
        storage=request.app.state.object_storage_provider()
        content=MultimodalReviewService(db, identity.principal.tenant_id).render_pdf_page(
            claim_id,evidence_id,storage=storage,bucket_name=settings.s3_bucket,page_number=page_number,bbox=parsed_bbox)
        return Response(content=content,media_type="image/png",headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})
    except Exception as exc:
        _handle(exc)
