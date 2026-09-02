from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.recovery_operations import recovery_operations_contract
from app.schemas.recovery_operations import *
from app.services.recovery_operations import RecoveryOperationsService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["recovery-operations"])
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
@router.get("/recovery-operations-model")
def model():return recovery_operations_contract()
@router.get("/recovery-operations")
def queue(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService(db,i.principal.tenant_id).queue(i.principal.user_id))
@router.get("/recovery-operations/portfolio")
def portfolio(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService(db,i.principal.tenant_id).portfolio(i.principal.user_id))
@router.post("/recovery-operations/from-remediation")
def create(payload:CreateRecoveryCaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService._view_case(RecoveryOperationsService(db,i.principal.tenant_id).create_from_remediation(payload.proposal_id,i.principal.user_id,idempotency_key=payload.idempotency_key)))
@router.get("/recovery-operations/{case_id}")
def workbench(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService(db,i.principal.tenant_id).workbench(case_id,i.principal.user_id))
@router.get("/recovery-operations/{case_id}/traceability")
def traceability(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.post("/recovery-operations/{case_id}/lease")
def lease(case_id:str,payload:AcquireRecoveryLeaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request)
    def f():
        r=RecoveryOperationsService(db,i.principal.tenant_id).acquire_lease(case_id,i.principal.user_id,expected_case_version=payload.expected_case_version,lease_minutes=payload.lease_minutes);return {"case":RecoveryOperationsService._view_case(r["case"]),"lease_token":r["lease_token"],"lease_version":r["lease_version"],"expires_at":r["expires_at"]}
    return _run(db,f)
@router.post("/recovery-operations/{case_id}/verify")
def verify(case_id:str,payload:VerifyRecoveryOutcomeRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService._view_outcome(RecoveryOperationsService(db,i.principal.tenant_id).verify_remediation_outcome(case_id,i.principal.user_id,lease_token=payload.lease_token,idempotency_key=payload.idempotency_key)))
@router.post("/recovery-operations/{case_id}/recoveries")
def recovery(case_id:str,payload:RecordRecoveryRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService._view_outcome(RecoveryOperationsService(db,i.principal.tenant_id).record_recovery(case_id,i.principal.user_id,amount=payload.amount,currency=payload.currency,external_reference=payload.external_reference,evidence_details=payload.evidence_details,lease_token=payload.lease_token,idempotency_key=payload.idempotency_key)))
@router.post("/recovery-operations/{case_id}/disputes")
def dispute(case_id:str,payload:ProviderDisputeRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService._view_dispute(RecoveryOperationsService(db,i.principal.tenant_id).submit_dispute(case_id,i.principal.user_id,external_reference=payload.external_reference,disputed_amount=payload.disputed_amount,currency=payload.currency,reason_code=payload.reason_code,statement=payload.statement,evidence_refs=payload.evidence_refs,idempotency_key=payload.idempotency_key)))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/resolve")
def resolve(case_id:str,dispute_id:str,payload:ResolveProviderDisputeRequest,request:Request,db:Session=Depends(get_db)):
    raise HTTPException(status_code=410,detail="direct provider dispute resolution retired; use /resolution/packet governed workflow")
@router.post("/recovery-operations/{case_id}/correspondence")
def correspondence(case_id:str,payload:RecoveryCorrespondenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService(db,i.principal.tenant_id).add_correspondence(case_id,i.principal.user_id,dispute_id=payload.dispute_id,direction=payload.direction,channel=payload.channel,subject=payload.subject,body=payload.body,external_message_id=payload.external_message_id,idempotency_key=payload.idempotency_key))
@router.post("/recovery-operations/{case_id}/close")
def close(case_id:str,payload:CloseRecoveryCaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:RecoveryOperationsService._view_case(RecoveryOperationsService(db,i.principal.tenant_id).close_case(case_id,i.principal.user_id,reason_code=payload.reason_code,rationale=payload.rationale,expected_case_version=payload.expected_case_version,lease_token=payload.lease_token,idempotency_key=payload.idempotency_key)))
