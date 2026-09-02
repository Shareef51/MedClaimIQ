from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.recovery_settlement import recovery_settlement_contract
from app.schemas.recovery_settlement import *
from app.services.recovery_settlement import RecoverySettlementService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["recovery-settlement"])
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
@router.get("/recovery-settlement-model")
def model():return recovery_settlement_contract()
@router.get("/recovery-settlements")
def queue(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).queue(i.principal.user_id))
@router.get("/recovery-settlements/portfolio")
def portfolio(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).portfolio(i.principal.user_id))
@router.post("/recovery-settlements/from-recovery/{recovery_case_id}")
def create(recovery_case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);key=request.headers.get("idempotency-key") or f"settlement:{recovery_case_id}";svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:svc._view_case(svc.create_from_recovery(recovery_case_id,i.principal.user_id,idempotency_key=key,trace_id=getattr(request.state,"trace_id",None))))
@router.get("/recovery-settlements/{case_id}")
def workbench(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).workbench(case_id,i.principal.user_id))
@router.get("/recovery-settlements/{case_id}/traceability")
def trace(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.post("/recovery-settlements/{case_id}/evidence")
def evidence(case_id:str,payload:SettlementEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:svc._view_evidence(svc.submit_evidence(case_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/recovery-settlements/{case_id}/evidence/{evidence_id}/verify")
def verify(case_id:str,evidence_id:str,payload:SettlementEvidenceVerificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:svc._view_evidence(svc.verify_evidence(case_id,evidence_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/recovery-settlements/{case_id}/evidence/{evidence_id}/ledger-correlation")
def correlate(case_id:str,evidence_id:str,payload:SettlementLedgerCorrelationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.correlate_ledger(case_id,evidence_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.workbench(case_id,i.principal.user_id))[1])
@router.post("/recovery-settlements/{case_id}/correspondence")
def correspondence(case_id:str,payload:SettlementCorrespondenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.add_correspondence(case_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.workbench(case_id,i.principal.user_id))[1])
@router.post("/recovery-settlements/{case_id}/certificate")
def certificate(case_id:str,payload:SettlementCertificatePrepareRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.prepare_certificate(case_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.workbench(case_id,i.principal.user_id))[1])
@router.post("/recovery-settlements/{case_id}/certificate/{certificate_id}/decision")
def certificate_decision(case_id:str,certificate_id:str,payload:SettlementCertificateDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.decide_certificate(case_id,certificate_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.workbench(case_id,i.principal.user_id))[1])
@router.post("/recovery-settlements/{case_id}/exceptions/{exception_id}/resolve")
def resolve_exception(case_id:str,exception_id:str,payload:SettlementExceptionResolveRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.resolve_exception(case_id,exception_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.workbench(case_id,i.principal.user_id))[1])
@router.get("/portal/recovery-settlements")
def portal_cases(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).provider_cases(i.principal.user_id))
@router.get("/portal/recovery-settlements/{case_id}")
def portal_workbench(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoverySettlementService(db,i.principal.tenant_id).provider_workbench(case_id,i.principal.user_id))
@router.post("/portal/recovery-settlements/{case_id}/evidence")
def portal_evidence(case_id:str,payload:SettlementEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:svc._view_evidence(svc.submit_evidence(case_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/portal/recovery-settlements/{case_id}/correspondence")
def portal_correspondence(case_id:str,payload:SettlementCorrespondenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=RecoverySettlementService(db,i.principal.tenant_id);return _run(db,lambda:(svc.add_correspondence(case_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.provider_workbench(case_id,i.principal.user_id))[1])
