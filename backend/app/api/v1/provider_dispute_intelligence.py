from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.provider_dispute_intelligence import provider_dispute_intelligence_contract
from app.schemas.provider_dispute_intelligence import *
from app.services.provider_dispute_intelligence import ProviderDisputeIntelligenceService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["provider-dispute-intelligence"])
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
@router.get("/provider-dispute-intelligence-model")
def model():return provider_dispute_intelligence_contract()
@router.get("/provider-dispute-intelligence")
def queue(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).reviewer_queue(i.principal.user_id))
@router.get("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence")
def workbench(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).workbench(case_id,dispute_id,i.principal.user_id))
@router.get("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/traceability")
def traceability(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).traceability(case_id,dispute_id,i.principal.user_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/evidence")
def evidence(case_id:str,dispute_id:str,payload:RegisterDisputeEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).process_evidence(case_id,dispute_id,payload.evidence_id,i.principal.user_id,trace_id=payload.trace_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/fhir")
def fhir(case_id:str,dispute_id:str,payload:RegisterFHIRDisputeEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).register_fhir(case_id,dispute_id,payload.snapshot_id,i.principal.user_id,trace_id=payload.trace_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/snapshot")
def snapshot(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).build_snapshot(case_id,dispute_id,i.principal.user_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/search")
def search(case_id:str,dispute_id:str,payload:SearchDisputeEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request)
    def f():
        r=ProviderDisputeIntelligenceService(db,i.principal.tenant_id).search(case_id,dispute_id,i.principal.user_id,payload.query,limit=payload.limit,trace_id=payload.trace_id);return {"run_id":r["run"].run_id,"pack_sha256":r["run"].pack_sha256,"items":[{"source_scope":x.source_scope,"source_id":x.source_id,"source_version":x.source_version,"rank":x.rank,"score":x.score,"text_preview":x.text_preview,"citation":x.citation} for x in r["items"]]}
    return _run(db,f)
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/recommendation")
def recommendation(case_id:str,dispute_id:str,payload:RunDisputeRecommendationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);q=payload.query or "Assess the provider dispute against governed recovery evidence, effective provider agreement and reimbursement policy.";return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).run_recommendation(case_id,dispute_id,i.principal.user_id,query=q,idempotency_key=payload.idempotency_key,trace_id=payload.trace_id))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/missing-evidence")
def missing(case_id:str,dispute_id:str,payload:RequestDisputeEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).request_missing_evidence(case_id,dispute_id,i.principal.user_id,document_types=payload.document_types,rationale=payload.rationale,idempotency_key=payload.idempotency_key))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/provider-response")
def provider_response(case_id:str,dispute_id:str,payload:ProviderDisputeResponseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).provider_response(case_id,dispute_id,i.principal.user_id,request_id=payload.request_id,statement=payload.statement,evidence_refs=payload.evidence_refs,idempotency_key=payload.idempotency_key))
@router.post("/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/checkpoints/{checkpoint_id}/resume")
def resume(case_id:str,dispute_id:str,checkpoint_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).resume_checkpoint(case_id,dispute_id,checkpoint_id,i.principal.user_id))
@router.post("/provider-dispute-intelligence/provider-agreements")
def agreement(payload:AddProviderAgreementRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).add_provider_agreement(i.principal.user_id,**payload.model_dump()))
@router.post("/provider-dispute-intelligence/reimbursement-policies")
def policy(payload:AddReimbursementPolicyRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).add_reimbursement_policy(i.principal.user_id,**payload.model_dump()))

@router.get("/portal/provider-disputes")
def portal_queue(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).provider_queue(i.principal.user_id))
@router.get("/portal/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence")
def portal_workbench(case_id:str,dispute_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).provider_workbench(case_id,dispute_id,i.principal.user_id))
@router.post("/portal/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/evidence")
def portal_evidence(case_id:str,dispute_id:str,payload:RegisterDisputeEvidenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).process_evidence(case_id,dispute_id,payload.evidence_id,i.principal.user_id,trace_id=payload.trace_id))
@router.post("/portal/recovery-operations/{case_id}/disputes/{dispute_id}/intelligence/provider-response")
def portal_provider_response(case_id:str,dispute_id:str,payload:ProviderDisputeResponseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:ProviderDisputeIntelligenceService(db,i.principal.tenant_id).provider_response(case_id,dispute_id,i.principal.user_id,request_id=payload.request_id,statement=payload.statement,evidence_refs=payload.evidence_refs,idempotency_key=payload.idempotency_key))
