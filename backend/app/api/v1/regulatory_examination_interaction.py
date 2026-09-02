from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_interaction import examination_interaction_contract
from app.schemas.regulatory_examination_interaction import *
from app.services.regulatory_examination_interaction import RegulatoryExaminationInteractionService
router=APIRouter(tags=["regulatory-examination-interaction"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationInteractionService(db,i.principal.tenant_id)
@router.get("/regulatory-examination-interactions/model")
def model(): return examination_interaction_contract()
@router.post("/regulatory-examination-interactions/meetings")
def create_meeting(payload:MeetingCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_meeting(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-interactions/statements")
def statement(payload:StatementCapture,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).capture_statement(i.principal.user_id,payload.model_dump())
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-interactions/summaries")
def summary(payload:MeetingSummaryRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).summarize(payload.model_dump())
@router.post("/regulatory-examination-interactions/commitments")
def commitment(payload:CommitmentCandidateCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_commitment_candidate(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-interactions/commitments/{commitment_id}/decision")
def commitment_decision(commitment_id:str,payload:CommitmentHumanDecision,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).decide_commitment(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-interactions/actions")
def action(payload:ActionItemCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_action(i.principal.user_id,payload.model_dump())
