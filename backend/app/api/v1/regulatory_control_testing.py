from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_control_testing import regulatory_control_testing_contract
from app.schemas.regulatory_control_testing import *
from app.services.regulatory_control_testing import RegulatoryControlTestingService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-control-testing"])
def _i(r):
    x=getattr(r.state,"identity",None)
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
def _svc(db,t):return RegulatoryControlTestingService(db,t)
@router.get('/regulatory-control-testing/model')
def model():return regulatory_control_testing_contract()
@router.get('/regulatory-control-testing/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-control-testing/plans')
def plan(payload:ControlTestPlanRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).create_plan(i.principal.user_id,**payload.model_dump()));return {"test_plan_id":r.test_plan_id,"plan_version":r.plan_version}
@router.post('/regulatory-control-testing/runs')
def run(payload:ControlTestRunRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r,s=_run(db,lambda:_svc(db,i.principal.tenant_id).prepare_run(i.principal.user_id,**payload.model_dump()));return {"test_run_id":r.test_run_id,"sample_ids":[x.sample_id for x in s],"population_watermark_sha256":r.population_watermark_sha256}
@router.post('/regulatory-control-testing/samples/{sample_id}/result')
def result(sample_id:str,payload:SampleResultRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);s=_run(db,lambda:_svc(db,i.principal.tenant_id).record_sample_result(i.principal.user_id,sample_id,**payload.model_dump()));return {"sample_id":s.sample_id,"result":s.result}
@router.get('/regulatory-control-testing/runs/{test_run_id}')
def view(test_run_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).view_run(i.principal.user_id,test_run_id))
@router.post('/regulatory-control-testing/runs/{test_run_id}/independent-conclusion')
def conclusion(test_run_id:str,payload:IndependentConclusionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);c=_run(db,lambda:_svc(db,i.principal.tenant_id).conclude(i.principal.user_id,test_run_id,**payload.model_dump()));return {"conclusion_id":c.conclusion_id,"version":c.conclusion_version,"effectiveness":c.effectiveness,"independent":c.independent}
