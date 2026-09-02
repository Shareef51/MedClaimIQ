from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_portfolio_oversight import regulatory_portfolio_contract
from app.schemas.regulatory_portfolio_oversight import *
from app.services.regulatory_portfolio_oversight import RegulatoryPortfolioOversightService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-portfolio-oversight"])
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
def _svc(db,t):return RegulatoryPortfolioOversightService(db,t)
@router.get('/regulatory-portfolio-oversight-model')
def model():return regulatory_portfolio_contract()
@router.get('/regulatory-portfolio-oversight/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-portfolio-oversight/controls')
def control(payload:EnterpriseControlCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).register_control(i.principal.user_id,**payload.model_dump()));return {"control_id":r.control_id,"control_key":r.control_key,"version":r.control_version}
@router.post('/regulatory-portfolio-oversight/controls/{control_id}/map')
def map_control(control_id:str,payload:ControlFindingMapRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).map_control(control_id,i.principal.user_id,**payload.model_dump()));return {"mapping_id":r.mapping_id,"control_id":r.control_id,"plan_id":r.plan_id}
@router.post('/regulatory-portfolio-oversight/snapshots')
def snapshot(payload:PortfolioSnapshotRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=_svc(db,i.principal.tenant_id);r=_run(db,lambda:svc.prepare_snapshot(i.principal.user_id,**payload.model_dump()));return svc.snapshot_view(r.snapshot_id,i.principal.user_id)
@router.get('/regulatory-portfolio-oversight/snapshots/{snapshot_id}')
def snapshot_view(snapshot_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).snapshot_view(snapshot_id,i.principal.user_id))
@router.post('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/testing-campaigns')
def campaign(snapshot_id:str,payload:TestingCampaignRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).create_testing_campaign(snapshot_id,i.principal.user_id,**payload.model_dump()));return {"campaign_id":r.campaign_id,"status":r.status,"control_ids":r.control_ids}
@router.post('/regulatory-portfolio-oversight/testing-campaigns/{campaign_id}/results')
def test_result(campaign_id:str,payload:TestingResultRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).record_test_result(campaign_id,i.principal.user_id,**payload.model_dump()));return {"result_id":r.result_id,"outcome":r.outcome,"payload_sha256":r.payload_sha256}
@router.post('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/risk-acceptances')
def risk(snapshot_id:str,payload:RiskAcceptanceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).request_risk_acceptance(snapshot_id,i.principal.user_id,**payload.model_dump()));return {"acceptance_id":r.acceptance_id,"risk_key":r.risk_key,"status":r.status}
@router.post('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/risk-acceptances/{risk_key}/decision')
def risk_decision(snapshot_id:str,risk_key:str,payload:RiskAcceptanceDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).decide_risk_acceptance(snapshot_id,risk_key,i.principal.user_id,**payload.model_dump()));return {"acceptance_id":r.acceptance_id,"status":r.status}
@router.post('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/management-attestation')
def attest(snapshot_id:str,payload:ManagementAttestationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).management_attest(snapshot_id,i.principal.user_id,**payload.model_dump()));return {"attestation_id":r.attestation_id,"conclusion":r.conclusion,"attestation_sha256":r.attestation_sha256}
@router.post('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/certify')
def certify(snapshot_id:str,payload:PortfolioCertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).certify_portfolio(snapshot_id,i.principal.user_id,**payload.model_dump()));return {"certification_id":r.certification_id,"conclusion":r.conclusion,"certification_sha256":r.certification_sha256}
@router.get('/regulatory-portfolio-oversight/snapshots/{snapshot_id}/board-package')
def package(snapshot_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).board_regulatory_package(snapshot_id,i.principal.user_id))
