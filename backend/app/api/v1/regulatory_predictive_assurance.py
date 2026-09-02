from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_predictive_assurance import regulatory_predictive_assurance_contract
from app.schemas.regulatory_predictive_assurance import *
from app.services.regulatory_predictive_assurance import RegulatoryPredictiveAssuranceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-predictive-assurance"])
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
def _svc(db,t):return RegulatoryPredictiveAssuranceService(db,t)
@router.get('/regulatory-predictive-assurance/model')
def model():return regulatory_predictive_assurance_contract()
@router.get('/regulatory-predictive-assurance/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-predictive-assurance/forecasts')
def forecast(payload:PredictiveForecastRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=_svc(db,i.principal.tenant_id);r=_run(db,lambda:svc.create_forecast(i.principal.user_id,**payload.model_dump()));return svc.view(r.forecast_id,i.principal.user_id)
@router.get('/regulatory-predictive-assurance/forecasts/{forecast_id}')
def view(forecast_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).view(forecast_id,i.principal.user_id))
@router.post('/regulatory-predictive-assurance/forecasts/{forecast_id}/scenarios')
def scenario(forecast_id:str,payload:ScenarioSimulationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).simulate(forecast_id,i.principal.user_id,**payload.model_dump()));return {"simulation_id":r.simulation_id,"scenario_key":r.scenario_key,"projected_metrics":r.projected_metrics,"recommendation":r.recommendation}
@router.post('/regulatory-predictive-assurance/forecasts/{forecast_id}/human-review')
def review(forecast_id:str,payload:PredictiveReviewRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).review_forecast(forecast_id,i.principal.user_id,**payload.model_dump()));return {"review_id":r.review_id,"sequence":r.review_sequence,"disposition":r.disposition}
