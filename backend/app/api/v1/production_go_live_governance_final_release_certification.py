from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.production_go_live_governance_final_release_certification import production_go_live_contract
from app.schemas.production_go_live_governance_final_release_certification import *
from app.services.production_go_live_governance_final_release_certification import ProductionGoLiveGovernanceFinalReleaseCertificationService
router=APIRouter(tags=["production-final-go-live"]); BASE="/production-final-go-live"
def _identity(r):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return ProductionGoLiveGovernanceFinalReleaseCertificationService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get(BASE+"/model")
def model(): return production_go_live_contract()
@router.post(BASE+"/release-manifest-assessment")
def manifest(p:ReleaseManifestRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).manifest_assessment(p.model_dump()))
@router.post(BASE+"/deployment-preflight")
def preflight(p:PreflightRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).preflight(p.model_dump()))
@router.post(BASE+"/canary-rollout")
def canary(p:CanaryRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).canary(p.model_dump()))
@router.post(BASE+"/post-deployment-verification")
def post(p:PostDeployRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).post_deploy(p.model_dump()))
@router.post(BASE+"/hypercare-assessment")
def hypercare(p:HypercareRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).hypercare(p.model_dump()))
@router.post(BASE+"/readiness")
def readiness(p:FinalReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).readiness(p.model_dump()))
@router.post(BASE+"/evidence-bundle")
def evidence(p:FinalReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).evidence(p.model_dump()))
@router.post(BASE+"/release-manifests")
def create_manifest(p:FinalReleaseManifestCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).create_manifest(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/go-live-approvals")
def approve(p:GoLiveApprovalCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).approve_go_live(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/deployment-verifications")
def verify(p:DeploymentVerificationCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).record_deployment_verification(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/final-certifications")
def certify(p:FinalReleaseCertificationCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).certify_final_release(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/hypercare-checkpoints")
def checkpoint(p:HypercareCheckpointCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).create_hypercare_checkpoint(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/hypercare-closures")
def close(p:HypercareClosureCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).close_hypercare(i.principal.user_id,p.model_dump()))
