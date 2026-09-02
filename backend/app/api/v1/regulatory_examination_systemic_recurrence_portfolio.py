from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_systemic_recurrence_portfolio import systemic_recurrence_portfolio_contract
from app.schemas.regulatory_examination_systemic_recurrence_portfolio import *
from app.services.regulatory_examination_systemic_recurrence_portfolio import RegulatoryExaminationSystemicRecurrencePortfolioService

router=APIRouter(tags=["regulatory-examination-systemic-recurrence-portfolio"])
def _identity(r: Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationSystemicRecurrencePortfolioService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-systemic-recurrence-portfolio/model")
def model(): return systemic_recurrence_portfolio_contract()
@router.post("/regulatory-examination-systemic-recurrence-portfolio/aggregate")
def aggregate(payload:PortfolioAggregationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).aggregate(payload.model_dump())
@router.post("/regulatory-examination-systemic-recurrence-portfolio/materiality")
def materiality(payload:MaterialityAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).materiality(payload.model_dump())
@router.post("/regulatory-examination-systemic-recurrence-portfolio/interventions")
def intervention(payload:EnterpriseInterventionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).create_intervention(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-systemic-recurrence-portfolio/program-decisions")
def program_decision(payload:InterventionProgramDecision,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).decide_program(i.principal.user_id,payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(403 if isinstance(e,PermissionError) else 422,str(e)) from e
@router.post("/regulatory-examination-systemic-recurrence-portfolio/independent-challenges")
def challenge(payload:IndependentChallengeCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
