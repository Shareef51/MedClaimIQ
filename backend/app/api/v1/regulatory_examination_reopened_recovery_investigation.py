from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reopened_recovery_investigation import reopened_recovery_investigation_contract
from app.schemas.regulatory_examination_reopened_recovery_investigation import *
from app.services.regulatory_examination_reopened_recovery_investigation import RegulatoryExaminationReopenedRecoveryInvestigationService
router=APIRouter(tags=["regulatory-examination-reopened-recovery-investigation"])
def _identity(r:Request):
 i=getattr(r.state,"identity",None)
 if i is None: raise HTTPException(401,"authenticated identity unavailable")
 return i
def _svc(db,i): return RegulatoryExaminationReopenedRecoveryInvestigationService(db,i.principal.tenant_id)
def _call(fn):
 try:return fn()
 except PermissionError as e: raise HTTPException(403,str(e)) from e
 except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-reopened-recovery-investigation/model")
def model(): return reopened_recovery_investigation_contract()
@router.post("/regulatory-examination-reopened-recovery-investigation/investigations")
def investigation(payload:ReopenedRecoveryInvestigationCreate,request:Request,db:Session=Depends(get_db)):
 i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reopened-recovery-investigation/decay-reconstruction")
def decay(payload:SystemicDecayReconstructionRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reconstruct_decay(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/assumption-validation")
def assumptions(payload:RecoveryAssumptionValidationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).validate_assumptions(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/root-cause-reassessment")
def roots(payload:DecayRootCauseReassessmentRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).reassess_root_causes(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/control-gap-analysis")
def gaps(payload:CrossEntityControlGapRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).analyze_control_gaps(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/regulator-impact")
def regulator(payload:RegulatorFollowUpImpactRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulator_impact(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/commitment-alignment")
def commitments(payload:CommitmentAlignmentRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).align_commitments(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/strategy-candidates")
def strategy(payload:RenewedRecoveryStrategyCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).create_strategy(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/independent-challenges")
def challenge(payload:IndependentChallengeRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_challenge(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reopened-recovery-investigation/authorization-readiness")
def readiness(payload:AuthorizationReadinessRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-reopened-recovery-investigation/authorizations")
def authorize(payload:RenewedRemediationAuthorizationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).authorize(i.principal.user_id,payload.model_dump()))
