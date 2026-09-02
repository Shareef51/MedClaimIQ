from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.api.v1.rag import _authorize_claim_read
from app.db.session import get_db
from app.domain.accounting_ledger import accounting_ledger_contract
from app.schemas.accounting_ledger import *
from app.services.accounting_ledger import AccountingLedgerService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["accounting-ledger"])
def _identity(request):
    i=getattr(request.state,"identity",None)
    if i is None:raise HTTPException(401,"authenticated identity is unavailable")
    return i
def _handle(exc):
    if isinstance(exc,LookupError):raise HTTPException(404,str(exc)) from exc
    if isinstance(exc,(ReviewConflictError,ReviewLockError)):raise HTTPException(409,str(exc)) from exc
    if isinstance(exc,(ValueError,PermissionError)):raise HTTPException(400,str(exc)) from exc
    raise exc
@router.get('/accounting-ledger-model')
def model():return accounting_ledger_contract()
@router.get('/claims/{claim_id}/accounting-ledger')
def snapshot(claim_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:return AccountingLedgerService(db,i.principal.tenant_id).claim_snapshot(claim_id)
    except Exception as exc:_handle(exc)
@router.get('/claims/{claim_id}/accounting-ledger/traceability')
def traceability(claim_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id)
    try:return AccountingLedgerService(db,i.principal.tenant_id).traceability(claim_id)
    except Exception as exc:_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/payment-intents/{intent_id}/era')
def era(claim_id:str,intent_id:str,payload:ERAIngestRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.record_era(claim_id,intent_id,i.principal.user_id,era_reference=payload.era_reference,payment_reference=payload.payment_reference,provider_ref=payload.provider_ref,paid_amount=payload.paid_amount,currency=payload.currency,remittance_payload=payload.remittance_payload,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'era_id':r.era_id,'payload_sha256':r.payload_sha256}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/payment-intents/{intent_id}/eft')
def eft(claim_id:str,intent_id:str,payload:EFTIngestRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.record_eft(claim_id,intent_id,i.principal.user_id,eft_reference=payload.eft_reference,bank_reference=payload.bank_reference,trace_number=payload.trace_number,amount=payload.amount,currency=payload.currency,status=payload.status,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'eft_id':r.eft_id,'payload_sha256':r.payload_sha256}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/payment-intents/{intent_id}/reconcile')
def reconcile(claim_id:str,intent_id:str,payload:ReconcileRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.reconcile(claim_id,intent_id,i.principal.user_id,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'reconciliation_id':r.reconciliation_id,'status':r.status,'journal_id':r.journal_id,'reconciliation_sha256':r.reconciliation_sha256}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/payment-intents/{intent_id}/returns')
def returned(claim_id:str,intent_id:str,payload:ReturnedPaymentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.record_return(claim_id,intent_id,i.principal.user_id,return_reference=payload.return_reference,return_code=payload.return_code,amount=payload.amount,reason=payload.reason,currency=payload.currency,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'return_id':r.return_id,'status':r.status,'journal_id':r.journal_id}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/payment-intents/{intent_id}/adjustments')
def adjustment(claim_id:str,intent_id:str,payload:AdjustmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.request_adjustment(claim_id,intent_id,i.principal.user_id,adjustment_type=payload.adjustment_type,amount=payload.amount,reason_code=payload.reason_code,rationale=payload.rationale,idempotency_key=payload.idempotency_key);db.commit();return {'adjustment_id':r.adjustment_id,'status':r.status}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/claims/{claim_id}/accounting-ledger/adjustments/{adjustment_id}/approve')
def approve_adjustment(claim_id:str,adjustment_id:str,payload:AdjustmentApproveRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_authorize_claim_read(db,i,claim_id);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.approve_adjustment(claim_id,adjustment_id,i.principal.user_id,rationale=payload.rationale,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'adjustment_id':r.adjustment_id,'status':r.status,'journal_id':r.journal_id}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/accounting-ledger/periods/{period_id}/close')
def close_period(period_id:str,payload:PeriodCloseRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.close_period(period_id,i.principal.user_id,expected_lock_version=payload.expected_lock_version,rationale=payload.rationale,idempotency_key=payload.idempotency_key,trace_id=getattr(request.state,'trace_id',None));db.commit();return {'period_id':r.period_id,'status':r.status,'lock_version':r.lock_version,'close_sha256':r.close_sha256}
    except Exception as exc:db.rollback();_handle(exc)
@router.post('/accounting-ledger/aging/refresh')
def refresh_aging(request:Request,db:Session=Depends(get_db)):
    i=_identity(request);svc=AccountingLedgerService(db,i.principal.tenant_id)
    try:r=svc.refresh_aging_queue(i.principal.user_id);db.commit();return {'items':len(r)}
    except Exception as exc:db.rollback();_handle(exc)
