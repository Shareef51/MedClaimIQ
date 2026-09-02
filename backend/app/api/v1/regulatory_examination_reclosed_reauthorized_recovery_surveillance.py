from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_reauthorized_recovery_surveillance import reclosed_reauthorized_recovery_surveillance_contract
from app.schemas.regulatory_examination_reclosed_reauthorized_recovery_surveillance import *
from app.services.regulatory_examination_reclosed_reauthorized_recovery_surveillance import RegulatoryExaminationReclosedReauthorizedRecoverySurveillanceService
router=APIRouter(tags=["regulatory-examination-reclosed-reauthorized-recovery-surveillance"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReclosedReauthorizedRecoverySurveillanceService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/model")
def model(): return reclosed_reauthorized_recovery_surveillance_contract()
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/repeated-recovery-decay")
def decay(payload:ReauthorizedRecoveryDecayRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).decay(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/systemic-risk-rebound")
def rebound(payload:ReauthorizedRiskReboundRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).rebound(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/cross-entity-recurrence")
def recurrence(payload:CrossEntityRecurrenceRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).recurrence(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/prior-reclosure-comparison")
def compare(payload:PriorReclosureComparisonRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).compare(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/examination-finding-correlation")
def findings(payload:ExaminationFindingCorrelationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).correlate_findings(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/regulator-followups")
def followups(payload:RegulatorFollowupLinkageRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulator_followups(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/investigations")
def investigation(payload:ReauthorizedRecoveryDecayInvestigationCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).create_investigation(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/independent-reassessments")
def reassessment(payload:IndependentRecoveryReassessmentCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).independent_reassess(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/supervisory-challenges")
def challenge(payload:SupervisoryRecoveryChallengeCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).supervisory_challenge(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/reopening-readiness")
def readiness(payload:EnterpriseRecoveryReopeningReadinessRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).readiness(payload.model_dump())
@router.post("/regulatory-examination-reclosed-reauthorized-recovery-surveillance/reopening-decisions")
def reopening(payload:EnterpriseRecoveryReopeningDecisionCreate,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).decide_reopening(i.principal.user_id,payload.model_dump()))
