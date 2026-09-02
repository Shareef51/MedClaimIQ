from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_renewed_recovery_execution import renewed_recovery_execution_contract
from app.schemas.regulatory_examination_renewed_recovery_execution import *
from app.services.regulatory_examination_renewed_recovery_execution import RegulatoryExaminationRenewedRecoveryExecutionService
router=APIRouter(tags=["regulatory-examination-renewed-recovery-execution"])
def _identity(r:Request):
 i=getattr(r.state,"identity",None)
 if i is None: raise HTTPException(401,"authenticated identity unavailable")
 return i
def _svc(db,i): return RegulatoryExaminationRenewedRecoveryExecutionService(db,i.principal.tenant_id)
def _call(fn):
 try:return fn()
 except PermissionError as e: raise HTTPException(403,str(e)) from e
 except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-renewed-recovery-execution/model")
def model(): return renewed_recovery_execution_contract()
@router.post("/regulatory-examination-renewed-recovery-execution/programs")
def programs(payload:RenewedRecoveryProgramCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_program(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-recovery-execution/control-rehabilitation")
def controls(payload:ControlRehabilitationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).control_rehabilitation(payload.model_dump())
@router.post("/regulatory-examination-renewed-recovery-execution/critical-path")
def path(payload:MilestoneCriticalPathRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).critical_path(payload.model_dump())
@router.post("/regulatory-examination-renewed-recovery-execution/implementation-drift")
def drift(payload:ImplementationDriftRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).detect_drift(payload.model_dump())
@router.post("/regulatory-examination-renewed-recovery-execution/recovery-kpis")
def kpis(payload:RecoveryKPIRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).kpis(payload.model_dump())
@router.post("/regulatory-examination-renewed-recovery-execution/independent-revalidation")
def revalidate(payload:IndependentRecoveryRevalidationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_revalidate(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-recovery-execution/readiness")
def readiness(payload:ExecutionReadinessRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-renewed-recovery-execution/executive-progress-reviews")
def review(payload:ExecutiveProgressReviewRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).executive_review(i.principal.user_id,payload.model_dump()))
