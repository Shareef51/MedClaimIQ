from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_reauthorized_recovery_investigation import reopened_reauthorized_recovery_investigation_contract
from app.schemas.regulatory_examination_reopened_reauthorized_recovery_investigation import *
from app.services.regulatory_examination_reopened_reauthorized_recovery_investigation import RegulatoryExaminationReopenedReauthorizedRecoveryInvestigationService

router = APIRouter(tags=["regulatory-examination-reopened-reauthorized-recovery-investigation"])

def _identity(r: Request):
    i = getattr(r.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryExaminationReopenedReauthorizedRecoveryInvestigationService(db, i.principal.tenant_id)

def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except ValueError as e: raise HTTPException(422, str(e)) from e

@router.get("/regulatory-examination-reopened-reauthorized-recovery-investigation/model")
def model(): return reopened_reauthorized_recovery_investigation_contract()

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/investigations")
def investigations(payload: ReopenedReauthorizedRecoveryInvestigationCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).create_investigation(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/evidence-reconstruction")
def evidence(payload: ReopenedRecoveryEvidenceReconstructionRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).reconstruct_evidence(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/root-cause-reconstruction")
def roots(payload: RepeatedFailureRootCauseReconstructionRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).reconstruct_root_causes(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/recertification-assumptions")
def assumptions(payload: PriorRecertificationAssumptionReassessmentRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).reassess_assumptions(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/re-rehabilitation-analysis")
def rehabilitation(payload: ReRehabilitationFailureAnalysisRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).analyze_re_rehabilitation(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/cross-entity-causality")
def causality(payload: ReopenedCrossEntityCausalityRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).causal_map(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/regulator-followup-impact")
def regulator(payload: ReopenedRecoveryRegulatorFollowupImpactRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).regulator_impact(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/strategy-candidates")
def strategies(payload: RenewedReauthorizedRecoveryStrategyCandidateCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).create_strategy_candidate(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/independent-challenges")
def challenge(payload: ReopenedRecoveryIndependentChallengeCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).independent_challenge(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/conclusions")
def conclusion(payload: ReopenedRecoveryInvestigationConclusionCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).conclude_investigation(i.principal.user_id, payload.model_dump()))

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/reauthorization-readiness")
def readiness(payload: ReopenedRecoveryReauthorizationReadinessRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).readiness(payload.model_dump())

@router.post("/regulatory-examination-reopened-reauthorized-recovery-investigation/reauthorizations")
def reauthorize(payload: SupervisoryRecoveryReauthorizationCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _call(lambda: _svc(db, i).authorize_recovery(i.principal.user_id, payload.model_dump()))
