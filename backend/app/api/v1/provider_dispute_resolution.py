from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.provider_dispute_resolution import provider_dispute_resolution_contract
from app.schemas.provider_dispute_resolution import *
from app.services.provider_dispute_resolution import ProviderDisputeResolutionService
from app.services.recovery_operations import RecoveryOperationsService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["provider-dispute-resolution"])
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
@router.get("/provider-dispute-resolution-model")
def model():return provider_dispute_resolution_contract()
@router.get("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution")
def snapshot(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeResolutionService(db,i.principal.tenant_id).snapshot(case_id,dispute_id,i.principal.user_id))
@router.get("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/traceability")
def trace(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeResolutionService(db,i.principal.tenant_id).traceability(case_id,dispute_id,i.principal.user_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/packet")
def packet(case_id:str,dispute_id:str,payload:ProviderDisputeDecisionPacketRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:svc.packet_view(svc.save_packet(case_id,dispute_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/packets/{packet_id}/lock")
def lock(case_id:str,dispute_id:str,packet_id:str,payload:ProviderDisputePacketLockRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:svc.packet_view(svc.lock_packet(case_id,dispute_id,packet_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/packets/{packet_id}/second-review")
def second(case_id:str,dispute_id:str,packet_id:str,payload:ProviderDisputeSecondReviewRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:svc.packet_view(svc.second_review(case_id,dispute_id,packet_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/packets/{packet_id}/close")
def close(case_id:str,dispute_id:str,packet_id:str,payload:ProviderDisputeFinalCloseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:(svc.close(case_id,dispute_id,packet_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)),svc.snapshot(case_id,dispute_id,i.principal.user_id))[1])

@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/referrals/{referral_id}/verify")
def verify_referral(case_id:str,dispute_id:str,referral_id:str,payload:ProviderDisputeReconciliationVerificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:svc.verify_reconciliation_referral(case_id,dispute_id,referral_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None)))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolution/finalize-recovery")
def finalize_recovery(case_id:str,dispute_id:str,payload:ProviderDisputeFinalRecoveryCloseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=ProviderDisputeResolutionService(db,i.principal.tenant_id);return _run(db,lambda:RecoveryOperationsService._view_case(svc.finalize_recovery_case(case_id,dispute_id,i.principal.user_id,**payload.model_dump(),trace_id=getattr(request.state,"trace_id",None))))
