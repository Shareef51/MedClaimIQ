from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_systemic_failure_investigation import systemic_failure_investigation_contract
from app.schemas.regulatory_examination_systemic_failure_investigation import *
from app.services.regulatory_examination_systemic_failure_investigation import RegulatoryExaminationSystemicFailureInvestigationService
router=APIRouter(tags=["regulatory-examination-systemic-failure-investigation"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationSystemicFailureInvestigationService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-systemic-failure-investigation/model")
def model(): return systemic_failure_investigation_contract()
@router.post("/regulatory-examination-systemic-failure-investigation/investigations")
def create_investigation(payload:SystemicFailureInvestigationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_investigation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/evidence-reconstruction")
def evidence(payload:EvidenceReconstructionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reconstruct_evidence(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/assumption-validation")
def assumptions(payload:PriorAssumptionValidationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/root-cause-reassessment")
def roots(payload:RootCauseReassessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reassess_root_cause(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/control-redesign-analysis")
def controls(payload:FailedControlRedesignRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).analyze_control_redesign(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/cross-entity-causality")
def causality(payload:CrossEntityCausalityRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).causal_map(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/regulator-follow-up-impact")
def regulator(payload:RegulatorFollowUpImpactRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).regulator_impact(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/strategy-candidates")
def strategy(payload:RenewedStrategyCandidateCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_strategy_candidate(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/independent-challenge")
def challenge(payload:IndependentChallengeRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-systemic-failure-investigation/reauthorization-readiness")
def readiness(payload:ReauthorizationReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-systemic-failure-investigation/reauthorizations")
def reauthorize(payload:RemediationReauthorizationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).authorize_remediation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-systemic-failure-investigation/conclusions")
def conclusion(payload:InvestigationConclusionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).conclude_investigation(i.principal.user_id,payload.model_dump()))
