from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_renewed_enterprise_remediation_execution import renewed_enterprise_remediation_execution_contract
from app.schemas.regulatory_examination_renewed_enterprise_remediation_execution import *
from app.services.regulatory_examination_renewed_enterprise_remediation_execution import RegulatoryExaminationRenewedEnterpriseRemediationExecutionService
router=APIRouter(tags=["regulatory-examination-renewed-enterprise-remediation-execution"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationRenewedEnterpriseRemediationExecutionService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-renewed-enterprise-remediation-execution/model")
def model(): return renewed_enterprise_remediation_execution_contract()
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/programs")
def program(payload:RenewedEnterpriseProgramCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_program(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/workstreams")
def workstream(payload:CorrectiveActionWorkstreamCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_workstream(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/control-transformations")
def transformation(payload:ControlTransformationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_control_transformation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/critical-path")
def critical(payload:CriticalPathRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).critical_path(payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/implementation-drift")
def drift(payload:ImplementationDriftRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).detect_drift(payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/effectiveness-kpis")
def kpis(payload:EffectivenessKpiRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).kpis(payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/independent-recovery-tests")
def recovery(payload:IndependentRecoveryTestCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_recovery_test(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/recovery-readiness")
def readiness(payload:RecoveryReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/residual-risk-reassessment")
def risk(payload:ResidualSystemicRiskRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).risk_reassessment(payload.model_dump())
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/residual-risk-decisions")
def risk_decision(payload:HumanResidualRiskDecision,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).decide_residual_risk(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-renewed-enterprise-remediation-execution/executive-progress")
def executive(payload:ExecutiveProgressDecision,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).executive_progress(i.principal.user_id,payload.model_dump()))
