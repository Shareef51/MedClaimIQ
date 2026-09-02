from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.production_performance_resilience_disaster_recovery_operational_readiness import production_performance_resilience_dr_operational_readiness_contract
from app.schemas.production_performance_resilience_disaster_recovery_operational_readiness import *
from app.services.production_performance_resilience_disaster_recovery_operational_readiness import ProductionPerformanceResilienceDisasterRecoveryOperationalReadinessService
router=APIRouter(tags=["production-operational-go-live-readiness"]); BASE="/operational-go-live-readiness"
def _identity(r):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return ProductionPerformanceResilienceDisasterRecoveryOperationalReadinessService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get(BASE+"/model")
def model(): return production_performance_resilience_dr_operational_readiness_contract()
@router.post(BASE+"/load-stress-soak")
def load(p:LoadStressSoakRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).load(p.model_dump()))
@router.post(BASE+"/tenant-noisy-neighbor")
def noisy(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).noisy_neighbor(p.model_dump()))
@router.post(BASE+"/ai-rag-agent-slo-cost")
def ai_slo(p:ComponentsRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).ai_slo(p.model_dump()))
@router.post(BASE+"/dependency-resilience")
def dep(p:DrillsRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).dependency(p.model_dump()))
@router.post(BASE+"/provider-outage-fallback")
def provider(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).provider(p.model_dump()))
@router.post(BASE+"/kubernetes-disruption")
def kube(p:DrillsRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).kubernetes(p.model_dump()))
@router.post(BASE+"/backup-restore")
def backup(p:BackupRestoreRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).backup_restore(p.model_dump()))
@router.post(BASE+"/dr-rpo-rto")
def dr(p:ServicesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).dr_objectives(p.model_dump()))
@router.post(BASE+"/failover-failback")
def failover(p:DrillsRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).failover(p.model_dump()))
@router.post(BASE+"/autoscaling-capacity")
def capacity(p:CapacityRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).capacity(p.model_dump()))
@router.post(BASE+"/observability-alert-runbooks")
def obs(p:ObservabilityRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).observability(p.model_dump()))
@router.post(BASE+"/incident-response-exercises")
def incident(p:IncidentExerciseRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).incident_response(p.model_dump()))
@router.post(BASE+"/readiness")
def readiness(p:OperationalReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).readiness(p.model_dump()))
@router.post(BASE+"/evidence-pack")
def pack(p:OperationalReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).evidence_pack(p.model_dump()))
@router.post(BASE+"/drill-runs")
def run(p:OperationalDrillRunCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).create_drill_run(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/certifications")
def certify(p:OperationalCertificationCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).certify(i.principal.user_id,p.model_dump()))
