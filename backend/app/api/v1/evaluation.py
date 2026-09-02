from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.evaluation import EvaluationRepository
from app.schemas.evaluation import EvaluationRunListItem,EvaluationRunRequest,EvaluationRunResponse,MetricResponse
from app.services.evaluation import EvaluationService,evaluation_model_contract
router=APIRouter(tags=["evaluation"])
def _identity(request):
    identity=getattr(request.state,"identity",None)
    if identity is None:raise HTTPException(401,"authenticated identity required")
    return identity
def _require(identity,run=False):
    allowed={UserRole.TENANT_ADMIN} if run else {UserRole.TENANT_ADMIN,UserRole.AUDITOR}
    if identity.principal.role not in allowed:raise HTTPException(403,"evaluation access denied")
@router.get("/evaluation-model")
def model_contract():return evaluation_model_contract()
@router.post("/evaluations/run",response_model=EvaluationRunResponse)
def run_eval(payload:EvaluationRunRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_require(i,True)
    try:s=EvaluationService(EvaluationRepository(db,i.principal.tenant_id)).run(dataset_name=payload.dataset,candidate_version=payload.candidate_version,trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"))
    except ValueError as e:raise HTTPException(422,str(e)) from e
    return EvaluationRunResponse(run_id=s.run_id,dataset_version=s.dataset_version,candidate_version=s.candidate_version,decision=s.decision.value,pass_rate=s.pass_rate,metrics=[MetricResponse(metric=m.metric,value=m.value,threshold=m.threshold,passed=m.passed,suite=m.suite) for m in s.metrics],regression_reasons=list(s.regression_reasons))
@router.get("/evaluations",response_model=list[EvaluationRunListItem])
def list_evals(request:Request,db:Session=Depends(get_db)):
    i=_identity(request);_require(i);return [EvaluationRunListItem(run_id=r.run_id,dataset_version=r.dataset_version,candidate_version=r.candidate_version,decision=r.decision,pass_rate=r.pass_rate) for r in EvaluationRepository(db,i.principal.tenant_id).list_runs()]
