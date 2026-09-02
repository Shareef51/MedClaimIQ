from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_repeated_recovery_failure_investigation import repeated_recovery_failure_investigation_contract
from app.schemas.regulatory_examination_repeated_recovery_failure_investigation import *
from app.services.regulatory_examination_repeated_recovery_failure_investigation import RegulatoryExaminationRepeatedRecoveryFailureInvestigationService
router=APIRouter(tags=["regulatory-examination-repeated-recovery-failure-investigation"])
def _identity(r):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationRepeatedRecoveryFailureInvestigationService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-repeated-recovery-failure-investigation/model")
def model(): return repeated_recovery_failure_investigation_contract()
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/investigations")
def investigation(payload:RepeatedRecoveryFailureInvestigationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_investigation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/evidence-reconstruction")
def evidence(payload:RecoveryEvidenceReconstructionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reconstruct_evidence(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/assumption-validation")
def assumptions(payload:RecoveryAssumptionValidationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/root-cause-reassessment")
def roots(payload:RecoveryRootCauseReassessmentRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).reassess_root_cause(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/rehabilitation-analysis")
def rehab(payload:FailedRehabilitationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).analyze_rehabilitation(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/cross-entity-causality")
def causality(payload:RecoveryCausalityRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).causal_map(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/regulator-impact")
def regulator(payload:RegulatorRecoveryImpactRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).regulator_impact(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/strategy-candidates")
def strategy(payload:RenewedRecoveryStrategyCandidateCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_strategy_candidate(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/independent-challenge")
def challenge(payload:RecoveryIndependentChallengeRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/reauthorization-readiness")
def readiness(payload:RecoveryReauthorizationReadinessRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/reauthorizations")
def reauthorize(payload:RecoveryRemediationReauthorizationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).authorize_remediation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-repeated-recovery-failure-investigation/conclusions")
def conclusion(payload:RecoveryInvestigationConclusionCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).conclude_investigation(i.principal.user_id,payload.model_dump()))
