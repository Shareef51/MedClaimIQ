from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.agents.model_client import OpenAIResponsesStructuredClient
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.regulatory_examination import regulatory_examination_contract
from app.schemas.regulatory_examination import *
from app.services.regulatory_examination import RegulatoryExaminationService
from app.services.review_workbench import ReviewConflictError, ReviewLockError
router=APIRouter(tags=["regulatory-examination"])

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
    settings=get_settings();client=OpenAIResponsesStructuredClient() if use_model and settings.regulatory_examination_response_model_enabled else None
    return RegulatoryExaminationService(db,tenant_id,model_client=client,response_model=settings.regulatory_examination_response_model)

@router.get('/regulatory-examination-model')
def model():return regulatory_examination_contract()
@router.get('/regulatory-examinations/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).dashboard(i.principal.user_id))
@router.post('/regulatory-examinations')
def open_case(payload:ExaminationOpenRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).open_inquiry(i.principal.user_id,**payload.model_dump()));return {"examination_case_id":r.examination_case_id,"status":r.status,"case_version":r.case_version,"response_due_at":r.response_due_at}
@router.post('/regulatory-examinations/{case_id}/document-requests')
def add_doc(case_id:str,payload:DocumentRequestCreate,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).add_document_request(case_id,i.principal.user_id,**payload.model_dump()));return {"document_request_id":r.document_request_id,"request_code":r.request_code,"status":r.status,"due_at":r.due_at}
@router.post('/regulatory-examinations/{case_id}/document-requests/{request_code}/satisfy')
def satisfy_doc(case_id:str,request_code:str,payload:DocumentRequestSatisfy,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).satisfy_document_request(case_id,request_code,i.principal.user_id,**payload.model_dump()));return {"document_request_id":r.document_request_id,"status":r.status}
@router.post('/regulatory-examinations/{case_id}/evidence-packs')
def evidence_pack(case_id:str,payload:EvidencePackRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).build_evidence_pack(case_id,i.principal.user_id,**payload.model_dump()));return {"evidence_pack_id":r.evidence_pack_id,"pack_version":r.pack_version,"payload_sha256":r.payload_sha256,"citation_count":len(r.citations)}
@router.post('/regulatory-examinations/{case_id}/evidence-search')
def search(case_id:str,payload:EvidenceSearchRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).search_evidence(case_id,i.principal.user_id,payload.query,payload.top_k))
@router.post('/regulatory-examinations/{case_id}/responses')
def draft(case_id:str,payload:ResponseDraftRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id,payload.use_ai_assistance).draft_response(case_id,i.principal.user_id,**payload.model_dump()));return {"response_id":r.response_id,"response_version":r.response_version,"status":r.status,"ai_assisted":r.ai_assisted,"ai_metadata":r.ai_metadata,"response_sha256":r.response_sha256}
@router.post('/regulatory-examinations/{case_id}/responses/{response_id}/approve')
def approve(case_id:str,response_id:str,payload:ResponseApprovalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).approve_response(case_id,response_id,i.principal.user_id,**payload.model_dump()));return {"response_id":r.response_id,"status":r.status,"approved_by_user_id":r.approved_by_user_id}
@router.post('/regulatory-examinations/{case_id}/responses/{response_id}/deliver')
def deliver(case_id:str,response_id:str,payload:ResponseDeliveryRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).deliver_response(case_id,response_id,i.principal.user_id,**payload.model_dump()));return {"correspondence_id":r.correspondence_id,"delivered":r.delivered,"payload_sha256":r.payload_sha256,"supplemental_submission_reference":r.supplemental_submission_reference}
@router.post('/regulatory-examinations/{case_id}/findings')
def finding(case_id:str,payload:FindingRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).record_finding(case_id,i.principal.user_id,**payload.model_dump()));return {"finding_id":r.finding_id,"finding_code":r.finding_code,"material":r.material,"status":r.status}
@router.post('/regulatory-examinations/{case_id}/findings/{finding_code}/resolve')
def resolve_finding(case_id:str,finding_code:str,payload:FindingResolveRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).resolve_finding(case_id,finding_code,i.principal.user_id,**payload.model_dump()));return {"finding_id":r.finding_id,"status":r.status}
@router.post('/regulatory-examinations/{case_id}/remediation-commitments')
def commitment(case_id:str,payload:CommitmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).add_commitment(case_id,i.principal.user_id,**payload.model_dump()));return {"commitment_id":r.commitment_id,"status":r.status,"due_at":r.due_at}
@router.post('/regulatory-examinations/{case_id}/remediation-commitments/{commitment_key}/complete')
def complete_commitment(case_id:str,commitment_key:str,payload:CommitmentCompleteRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).complete_commitment(case_id,commitment_key,i.principal.user_id,**payload.model_dump()));return {"commitment_id":r.commitment_id,"status":r.status}
@router.post('/regulatory-examinations/{case_id}/close')
def close(case_id:str,payload:CloseExaminationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);r=_run(db,lambda:_svc(db,i.principal.tenant_id).close_examination(case_id,i.principal.user_id,**payload.model_dump()));return {"examination_case_id":r.examination_case_id,"status":r.status,"case_version":r.case_version}
@router.get('/regulatory-examinations/{case_id}/traceability')
def trace(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.get('/regulatory-examinations/{case_id}/audit-export')
def export(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:_svc(db,i.principal.tenant_id).audit_export(case_id,i.principal.user_id))
