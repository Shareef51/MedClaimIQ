from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.agents.model_client import OpenAIResponsesStructuredClient
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.regulatory_remediation import regulatory_remediation_contract
from app.schemas.regulatory_remediation import *
from app.services.regulatory_remediation import RegulatoryRemediationService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["regulatory-remediation"])
def _i(request):
    x=getattr(request.state,"identity",None)
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
def _svc(db,tenant_id,use_model=False):
    settings=get_settings();client=OpenAIResponsesStructuredClient() if use_model and settings.regulatory_remediation_recommendation_model_enabled else None
    return RegulatoryRemediationService(db,tenant_id,model_client=client,recommendation_model=settings.regulatory_remediation_recommendation_model)
@router.get('/regulatory-remediation-model')
def model():return regulatory_remediation_contract()
@router.get('/regulatory-remediation/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-examinations/{case_id}/remediation-plans')
def create_plan(case_id:str,payload:RemediationPlanCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=_svc(db,i.principal.tenant_id,payload.use_ai_assistance);r=_run(db,lambda:svc.create_plan(case_id,i.principal.user_id,**payload.model_dump()));return svc._plan_view(r)
@router.post('/regulatory-remediation/{plan_id}/approve')
def approve(plan_id:str,payload:RemediationPlanApprovalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);svc=_svc(db,i.principal.tenant_id);r=_run(db,lambda:svc.approve_plan(plan_id,i.principal.user_id,**payload.model_dump()));return svc._plan_view(r)
@router.post('/regulatory-remediation/{plan_id}/tasks')
def add_task(plan_id:str,payload:RemediationTaskCreateRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).add_task(plan_id,i.principal.user_id,**payload.model_dump()));return {"task_id":r.task_id,"task_key":r.task_key,"status":r.status,"due_at":r.due_at}
@router.post('/regulatory-remediation/{plan_id}/tasks/{task_key}/complete')
def complete_task(plan_id:str,task_key:str,payload:RemediationTaskCompleteRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).complete_task(plan_id,task_key,i.principal.user_id,**payload.model_dump()));return {"task_id":r.task_id,"status":r.status,"completed_at":r.completed_at}
@router.post('/regulatory-remediation/{plan_id}/checkpoints')
def checkpoint(plan_id:str,payload:RemediationCheckpointRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).lock_checkpoint(plan_id,i.principal.user_id,**payload.model_dump()));return {"checkpoint_id":r.checkpoint_id,"payload_sha256":r.payload_sha256,"locked_at":r.locked_at}
@router.post('/regulatory-remediation/{plan_id}/retests')
def retest(plan_id:str,payload:ControlRetestRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).retest_control(plan_id,i.principal.user_id,**payload.model_dump()));return {"retest_id":r.retest_id,"outcome":r.outcome,"payload_sha256":r.payload_sha256}
@router.post('/regulatory-remediation/{plan_id}/waivers')
def waiver(plan_id:str,payload:WaiverRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).request_waiver(plan_id,i.principal.user_id,**payload.model_dump()));return {"waiver_id":r.waiver_id,"waiver_key":r.waiver_key,"status":r.status}
@router.post('/regulatory-remediation/{plan_id}/waivers/{waiver_key}/decision')
def waiver_decision(plan_id:str,waiver_key:str,payload:WaiverDecisionRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).decide_waiver(plan_id,waiver_key,i.principal.user_id,**payload.model_dump()));return {"waiver_id":r.waiver_id,"status":r.status,"decided_by_user_id":r.decided_by_user_id}
@router.post('/regulatory-remediation/{plan_id}/followups')
def followup(plan_id:str,payload:FollowupDraftRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).draft_followup(plan_id,i.principal.user_id,**payload.model_dump()));return {"followup_id":r.followup_id,"version":r.response_version,"status":r.status,"response_sha256":r.response_sha256}
@router.post('/regulatory-remediation/{plan_id}/followups/{followup_id}/approve')
def followup_approve(plan_id:str,followup_id:str,payload:FollowupApprovalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).approve_followup(plan_id,followup_id,i.principal.user_id,**payload.model_dump()));return {"followup_id":r.followup_id,"status":r.status,"approved_by_user_id":r.approved_by_user_id}
@router.post('/regulatory-remediation/{plan_id}/certify-closure')
def certify(plan_id:str,payload:ClosureCertificationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).certify_closure(plan_id,i.principal.user_id,**payload.model_dump()));return {"certification_id":r.certification_id,"conclusion":r.conclusion,"certification_sha256":r.certification_sha256,"certified_at":r.certified_at}
@router.get('/regulatory-remediation/{plan_id}/traceability')
def trace(plan_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).traceability(plan_id,i.principal.user_id))
@router.get('/regulatory-remediation/{plan_id}/audit-export')
def export(plan_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).audit_export(plan_id,i.principal.user_id))
