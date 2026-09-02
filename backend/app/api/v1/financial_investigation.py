from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.financial_investigation import financial_investigation_contract
from app.schemas.financial_investigation import *
from app.services.financial_investigation import FinancialInvestigationService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
router=APIRouter(tags=["financial-investigation"])
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
@router.get("/financial-investigation-model")
def model():return financial_investigation_contract()
@router.get("/financial-investigations")
def queue(request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService(db,i.principal.tenant_id).queue(i.principal.user_id))
@router.post("/financial-investigations/from-anomaly")
def create(payload:CreateInvestigationCaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService(db,i.principal.tenant_id).create_from_anomaly(payload.investigation_id,i.principal.user_id,idempotency_key=payload.idempotency_key))
@router.get("/financial-investigations/{case_id}")
def workbench(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService(db,i.principal.tenant_id).workbench(case_id,i.principal.user_id))
@router.get("/financial-investigations/{case_id}/traceability")
def traceability(case_id:str,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService(db,i.principal.tenant_id).traceability(case_id,i.principal.user_id))
@router.post("/financial-investigations/{case_id}/lease")
def lease(case_id:str,payload:AcquireInvestigationLeaseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request)
    def f():
        r=FinancialInvestigationService(db,i.principal.tenant_id).acquire_lease(case_id,i.principal.user_id,expected_case_version=payload.expected_case_version,lease_minutes=payload.lease_minutes)
        return {"case":FinancialInvestigationService._case_view(r["case"]),"lease_token":r["lease_token"],"lease_version":r["lease_version"],"expires_at":r["expires_at"]}
    return _run(db,f)
@router.post("/financial-investigations/{case_id}/annotations")
def annotate(case_id:str,payload:InvestigationAnnotationRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService(db,i.principal.tenant_id).annotate(case_id,i.principal.user_id,target_type=payload.target_type,target_id=payload.target_id,body=payload.body,tags=payload.tags,idempotency_key=payload.idempotency_key))
@router.post("/financial-investigations/{case_id}/root-cause")
def root(case_id:str,payload:RootCauseRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService._case_view(FinancialInvestigationService(db,i.principal.tenant_id).classify_root_cause(case_id,i.principal.user_id,root_cause_code=payload.root_cause_code,rationale=payload.rationale,ai_disagreement_rationale=payload.ai_disagreement_rationale,expected_case_version=payload.expected_case_version,lease_token=payload.lease_token)))
@router.post("/financial-investigations/{case_id}/remediation")
def propose(case_id:str,payload:RemediationProposalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService._proposal_view(FinancialInvestigationService(db,i.principal.tenant_id).propose_remediation(case_id,i.principal.user_id,remediation_type=payload.remediation_type,amount=payload.amount,currency=payload.currency,reason_code=payload.reason_code,rationale=payload.rationale,idempotency_key=payload.idempotency_key,lease_token=payload.lease_token)))
@router.post("/financial-investigations/{case_id}/remediation/{proposal_id}/approve")
def approve(case_id:str,proposal_id:str,payload:RemediationApprovalRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService._proposal_view(FinancialInvestigationService(db,i.principal.tenant_id).approve_remediation(case_id,proposal_id,i.principal.user_id,rationale=payload.rationale,idempotency_key=payload.idempotency_key)))
@router.post("/financial-investigations/{case_id}/remediation/{proposal_id}/execute")
def execute(case_id:str,proposal_id:str,payload:dict,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService._proposal_view(FinancialInvestigationService(db,i.principal.tenant_id).execute_referral(case_id,proposal_id,i.principal.user_id,lease_token=str(payload.get("lease_token","")),idempotency_key=str(payload.get("idempotency_key","")))))
@router.post("/financial-investigations/{case_id}/close")
def close(case_id:str,payload:CaseClosureRequest,request:Request,db:Session=Depends(get_db)):
    i=_i(request);return _run(db,lambda:FinancialInvestigationService._case_view(FinancialInvestigationService(db,i.principal.tenant_id).close_case(case_id,i.principal.user_id,reason_code=payload.reason_code,rationale=payload.rationale,expected_case_version=payload.expected_case_version,lease_token=payload.lease_token,idempotency_key=payload.idempotency_key)))
