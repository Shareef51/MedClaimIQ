from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_commitment_lifecycle import commitment_lifecycle_contract
from app.schemas.regulatory_examination_commitment_lifecycle import *
from app.services.regulatory_examination_commitment_lifecycle import RegulatoryExaminationCommitmentLifecycleService
router=APIRouter(tags=["regulatory-examination-commitment-lifecycle"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationCommitmentLifecycleService(db,i.principal.tenant_id)
@router.get("/regulatory-examination-commitments/model")
def model(): return commitment_lifecycle_contract()
@router.post("/regulatory-examination-commitments")
def register(payload:CommitmentRegisterCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).register(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-commitments/milestones")
def milestone(payload:MilestoneCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).add_milestone(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-commitments/evidence")
def evidence(payload:EvidenceLinkCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).link_evidence(i.principal.user_id,payload.model_dump())
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-commitments/effectiveness-validations")
def validate(payload:EffectivenessValidationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).validate_effectiveness(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-commitments/reconcile")
def reconcile(payload:ReconciliationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reconcile(payload.model_dump())
@router.post("/regulatory-examination-commitments/amendments")
def amendment(payload:AmendmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).request_amendment(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-commitments/{commitment_id}/certify-completion")
def certify(commitment_id:str,payload:CompletionCertification,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:return _svc(db,i).certify_completion(i.principal.user_id,commitment_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-commitments/follow-ups")
def follow_up(payload:FollowUpCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_follow_up(i.principal.user_id,payload.model_dump())
