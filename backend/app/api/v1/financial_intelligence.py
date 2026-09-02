from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read
from app.agents.model_client import OpenAIResponsesStructuredClient
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.financial_intelligence import financial_intelligence_contract
from app.schemas.financial_intelligence import FinancialCopilotRequest, FinancialInvestigationRequest
from app.services.financial_intelligence import FinancialIntelligenceService
from app.services.review_workbench import ReviewConflictError, ReviewLockError
router=APIRouter(tags=["financial-intelligence"])
def _identity(request):
    i=getattr(request.state,"identity",None)
    if i is None:raise HTTPException(401,"authenticated identity is unavailable")
    return i
def _handle(exc):
    if isinstance(exc,LookupError):raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)):raise HTTPException(409,str(exc)) from exc
    if isinstance(exc,(ValueError,PermissionError)):raise HTTPException(400,str(exc)) from exc
    raise exc
@router.get('/financial-intelligence-model')
def model():return financial_intelligence_contract()
@router.get('/claims/{claim_id}/financial-intelligence')
def claim_analytics(claim_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:r=FinancialIntelligenceService(db,i.principal.tenant_id).claim_analytics(claim_id,persist=True);db.commit();return r
    except Exception as exc:db.rollback();_handle(exc)
@router.get('/financial-intelligence/portfolio')
def portfolio(request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try:r=FinancialIntelligenceService(db,i.principal.tenant_id).portfolio(i.principal.user_id,persist=True);db.commit();return r
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/financial-intelligence/investigations')
def investigate(claim_id:str,payload:FinancialInvestigationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:r=FinancialIntelligenceService(db,i.principal.tenant_id).investigate(claim_id,i.principal.user_id,payload.anomaly_code);db.commit();return r
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/financial-intelligence/copilot')
def copilot(payload:FinancialCopilotRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    if payload.claim_id:_authorize_claim_read(db,i,payload.claim_id)
    try:
        settings=get_settings();client=OpenAIResponsesStructuredClient() if settings.financial_intelligence_copilot_model_enabled else None
        r=FinancialIntelligenceService(db,i.principal.tenant_id,model_client=client,copilot_model=settings.financial_intelligence_copilot_model).copilot(i.principal.user_id,payload.query,claim_id=payload.claim_id,top_k=payload.top_k);db.commit();return r
    except Exception as exc:db.rollback();_handle(exc)
