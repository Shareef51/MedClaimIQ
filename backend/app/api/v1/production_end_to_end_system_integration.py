from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.production_end_to_end_system_integration import production_end_to_end_system_integration_contract
from app.schemas.production_end_to_end_system_integration import *
from app.services.production_end_to_end_system_integration import ProductionEndToEndSystemIntegrationService
router=APIRouter(tags=["production-end-to-end-system-integration"])
BASE="/release-candidate-hardening"
def _identity(request:Request):
    identity=getattr(request.state,"identity",None)
    if identity is None: raise HTTPException(401,"authenticated identity unavailable")
    return identity
def _svc(db,identity): return ProductionEndToEndSystemIntegrationService(db,identity.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
@router.get(BASE+"/model")
def model(): return production_end_to_end_system_integration_contract()
@router.post(BASE+"/golden-journeys")
def golden(p:GoldenJourneyRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).golden_journey(p.model_dump()))
@router.post(BASE+"/api-contract-regression")
def contracts(p:ApiContractRegressionRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).api_contracts(p.model_dump()))
@router.post(BASE+"/tenant-isolation")
def tenant(p:TenantIsolationRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).tenant_isolation(p.model_dump()))
@router.post(BASE+"/workflow-recovery")
def recovery(p:WorkflowRecoveryRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).workflow_recovery(p.model_dump()))
@router.post(BASE+"/event-sse-integrity")
def event_sse(p:EventSSEIntegrityRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).event_sse(p.model_dump()))
@router.post(BASE+"/failure-injection")
def failure(p:FailureInjectionRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).failure_injection(p.model_dump()))
@router.post(BASE+"/migration-chain")
def migrations(p:MigrationChainRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).migration_chain(p.model_dump()))
@router.post(BASE+"/readiness")
def readiness(p:ReleaseCandidateReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).readiness(p.model_dump()))
@router.post(BASE+"/report")
def report(p:ReleaseCandidateReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).report(p.model_dump()))
@router.post(BASE+"/integration-runs")
def integration_run(p:IntegrationRunCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).create_integration_run(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/candidate-decisions")
def decision(p:ReleaseCandidateDecisionCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).decide_candidate(i.principal.user_id,p.model_dump()))
