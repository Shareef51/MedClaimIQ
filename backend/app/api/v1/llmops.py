from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.llmops import LLMOpsRepository
from app.schemas.llmops import LLMOpsSummaryResponse, SLOEvaluateRequest
from app.services.llmops import LLMOpsService, llmops_model_contract
from app.core.config import get_settings

router=APIRouter(tags=["llmops"])

def _identity(request):
    identity=getattr(request.state,"identity",None)
    if identity is None: raise HTTPException(401,"authenticated identity required")
    return identity

def _require(identity, *, mutate=False):
    allowed={UserRole.TENANT_ADMIN} if mutate else {UserRole.TENANT_ADMIN,UserRole.AUDITOR}
    if identity.principal.role not in allowed: raise HTTPException(403,"LLMOps access denied")

@router.get("/llmops-model")
def model_contract(): return llmops_model_contract(get_settings())

@router.get("/llmops/summary",response_model=LLMOpsSummaryResponse)
def summary(request:Request,window_minutes:int=60,db:Session=Depends(get_db)):
    i=_identity(request);_require(i);return LLMOpsService(LLMOpsRepository(db,i.principal.tenant_id),get_settings()).summary(window_minutes)

@router.post("/llmops/slos/evaluate")
def evaluate_slos(payload:SLOEvaluateRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_require(i,mutate=True);rows=LLMOpsService(LLMOpsRepository(db,i.principal.tenant_id),get_settings()).evaluate_slos(payload.window_minutes);return {"created":len(rows),"events":[{"id":r.slo_event_id,"kind":r.slo_kind,"severity":r.severity} for r in rows]}

@router.get("/llmops/traces/{trace_id}")
def trace_detail(trace_id:str,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_require(i);return LLMOpsService(LLMOpsRepository(db,i.principal.tenant_id),get_settings()).trace_detail(trace_id)
