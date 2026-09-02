from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.agents.model_client import OpenAIResponsesStructuredClient
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.recovery_settlement_intelligence import recovery_settlement_intelligence_contract
from app.schemas.recovery_settlement_intelligence import SettlementIntelligenceCopilotRequest,SettlementIntelligenceInvestigationRequest,StatementPublishRequest
from app.services.recovery_settlement_intelligence import RecoverySettlementIntelligenceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["recovery-settlement-intelligence"])
def _i(request):
    x=getattr(request.state,"identity",None)
    if x is None:raise HTTPException(401,"authenticated identity unavailable")
    return x
def _run(db,fn):
    try:r=fn();db.commit();return r
    except Exception as e:
        db.rollback()
        if isinstance(e,LookupError):raise HTTPException(404,str(e)) from e
        if isinstance(e,(ReviewConflictError,ReviewLockError)):raise HTTPException(409,str(e)) from e
        if isinstance(e,(ValueError,PermissionError)):raise HTTPException(400,str(e)) from e
        raise
@router.get("/recovery-settlement-intelligence-model")
def model():return recovery_settlement_intelligence_contract()
@router.get("/recovery-settlement-intelligence/portfolio")
def portfolio(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).portfolio(i.principal.user_id,persist=True))
@router.get("/recovery-settlement-intelligence/providers/{provider_id}/statement")
def provider_statement(provider_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).provider_statement(provider_id,i.principal.user_id,persist=True))
@router.post("/recovery-settlement-intelligence/statements/{statement_id}/publish")
def publish(statement_id:str,payload:StatementPublishRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementIntelligenceService(db,i.principal.tenant_id);return _run(db,lambda:{"delivery_id":svc.publish_statement(statement_id,i.principal.user_id,idempotency_key=payload.idempotency_key).delivery_id,"delivered":True})
@router.get("/recovery-settlement-intelligence/accounting-periods/{period_id}/closeout-report")
def closeout(period_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).accounting_closeout_report(period_id,i.principal.user_id,persist=True))
@router.get("/recovery-settlement-intelligence/cases/{case_id}/traceability")
def traceability(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.post("/recovery-settlement-intelligence/cases/{case_id}/investigations")
def investigate(case_id:str,payload:SettlementIntelligenceInvestigationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).investigate_exception(case_id,i.principal.user_id,payload.exception_code))
@router.post("/recovery-settlement-intelligence/copilot")
def copilot(payload:SettlementIntelligenceCopilotRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);settings=get_settings();client=OpenAIResponsesStructuredClient() if settings.financial_intelligence_copilot_model_enabled else None
    return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id,model_client=client,copilot_model=settings.financial_intelligence_copilot_model).copilot(i.principal.user_id,payload.query,provider_organization_id=payload.provider_organization_id,settlement_case_id=payload.settlement_case_id,top_k=payload.top_k))
@router.get("/portal/recovery-balance-statements")
def portal_statements(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementIntelligenceService(db,i.principal.tenant_id).provider_portal_statements(i.principal.user_id))
