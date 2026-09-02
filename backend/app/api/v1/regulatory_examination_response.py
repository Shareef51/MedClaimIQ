from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_response import examination_response_contract
from app.schemas.regulatory_examination_response import *
from app.services.regulatory_examination_response import RegulatoryExaminationResponseService
router=APIRouter(tags=["regulatory-examination-response"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationResponseService(db,i.principal.tenant_id)
@router.get("/regulatory-examination-response/model")
def model(): return examination_response_contract()
@router.post("/regulatory-examination-response/questions")
def question(payload:ExaminerQuestionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).intake_question(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-response/evidence-refresh")
def refresh(payload:EvidenceRefreshRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).refresh_evidence(payload.model_dump())
@router.post("/regulatory-examination-response/revisions")
def revision(payload:ResponseRevisionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_revision(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-response/revisions/{revision_id}/review")
def review(revision_id:str,payload:HumanReviewDecision,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).review_revision(i.principal.user_id,revision_id,**payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(409,str(e)) from e
@router.post("/regulatory-examination-response/submissions")
def submission(payload:SubmissionRecordRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).authorize_submission(i.principal.user_id,payload.model_dump(),getattr(i.principal,"role",""))
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-response/receipts")
def receipt(payload:ReceiptRecordRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).record_receipt(i.principal.user_id,payload.model_dump())
