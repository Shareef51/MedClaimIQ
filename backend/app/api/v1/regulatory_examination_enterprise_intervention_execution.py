from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_enterprise_intervention_execution import enterprise_intervention_execution_contract
from app.schemas.regulatory_examination_enterprise_intervention_execution import *
from app.services.regulatory_examination_enterprise_intervention_execution import RegulatoryExaminationEnterpriseInterventionExecutionService

router=APIRouter(tags=["regulatory-examination-enterprise-intervention-execution"])
def _identity(r: Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationEnterpriseInterventionExecutionService(db,i.principal.tenant_id)

@router.get("/regulatory-examination-enterprise-intervention-execution/model")
def model(): return enterprise_intervention_execution_contract()
@router.post("/regulatory-examination-enterprise-intervention-execution/programs")
def create_program(payload:InterventionProgramPlanCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).create_program(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-execution/readiness")
def readiness(payload:ProgramExecutionAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).execution_readiness(payload.model_dump())
@router.post("/regulatory-examination-enterprise-intervention-execution/checkpoints")
def checkpoint(payload:ImplementationCheckpointCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).checkpoint(i.principal.user_id,payload.model_dump())
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-execution/capacity-risk")
def capacity(payload:ResourceCapacityAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).capacity_risk(payload.model_dump())
@router.post("/regulatory-examination-enterprise-intervention-execution/dependency-concentration")
def deps(payload:DependencyConcentrationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).dependency_concentration(payload.model_dump())
@router.post("/regulatory-examination-enterprise-intervention-execution/independent-assurance")
def assurance(payload:IndependentEffectivenessAssessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).independent_assurance(i.principal.user_id,payload.model_dump())
    except PermissionError as e: raise HTTPException(403,str(e)) from e
@router.post("/regulatory-examination-enterprise-intervention-execution/executive-certification")
def certification(payload:ExecutiveCertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request)
    try: return _svc(db,i).executive_certification(i.principal.user_id,payload.model_dump())
    except (PermissionError,ValueError) as e: raise HTTPException(403 if isinstance(e,PermissionError) else 422,str(e)) from e
