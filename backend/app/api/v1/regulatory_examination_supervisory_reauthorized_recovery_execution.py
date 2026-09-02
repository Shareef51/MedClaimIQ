from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_supervisory_reauthorized_recovery_execution import supervisory_reauthorized_recovery_execution_contract
from app.schemas.regulatory_examination_supervisory_reauthorized_recovery_execution import *
from app.services.regulatory_examination_supervisory_reauthorized_recovery_execution import RegulatoryExaminationSupervisoryReauthorizedRecoveryExecutionService

router = APIRouter(tags=["regulatory-examination-supervisory-reauthorized-recovery-execution"])

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationSupervisoryReauthorizedRecoveryExecutionService(db, i.principal.tenant_id)

def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get("/regulatory-examination-supervisory-reauthorized-recovery-execution/model")
def model(): return supervisory_reauthorized_recovery_execution_contract()

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/programs")
def programs(payload: SupervisoryReauthorizedRecoveryProgramCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).create_program(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/progress")
def progress(payload: SupervisoryProgramProgressRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).progress(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/control-retransformation")
def controls(payload: EnterpriseControlReTransformationRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).control_retransformation(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/deployment-sequence")
def sequence(payload: SupervisoryDeploymentSequenceRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).deployment_sequence(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/critical-path")
def path(payload: SupervisoryCriticalPathRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).critical_path(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/implementation-drift")
def drift(payload: SupervisoryImplementationDriftRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).detect_drift(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/recovery-kpis")
def kpis(payload: SupervisoryRecoveryKPIRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).kpis(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/checkpoints")
def checkpoint(payload: SupervisoryExecutionCheckpointCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).create_checkpoint(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/independent-assurance")
def assurance(payload: SupervisoryIndependentRecoveryAssuranceRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).independent_assurance(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/readiness")
def readiness(payload: SupervisoryExecutionReadinessRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).readiness(payload.model_dump())

@router.post("/regulatory-examination-supervisory-reauthorized-recovery-execution/executive-progress-reviews")
def review(payload: SupervisoryExecutiveProgressReviewRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).executive_review(i.principal.user_id, payload.model_dump()))
