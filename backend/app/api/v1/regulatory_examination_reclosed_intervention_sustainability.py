from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_intervention_sustainability import reclosed_intervention_sustainability_contract
from app.schemas.regulatory_examination_reclosed_intervention_sustainability import *
from app.services.regulatory_examination_reclosed_intervention_sustainability import RegulatoryExaminationReclosedInterventionSustainabilityService

router=APIRouter(tags=["regulatory-examination-reclosed-intervention-sustainability"])
def _identity(r:Request):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReclosedInterventionSustainabilityService(db,i.principal.tenant_id)
def _call(fn):
    try: return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e

@router.get("/regulatory-examination-reclosed-intervention-sustainability/model")
def model(): return reclosed_intervention_sustainability_contract()
@router.post("/regulatory-examination-reclosed-intervention-sustainability/observations")
def observation(payload:SustainabilityObservationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).observe_sustainability(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/multi-cycle-recurrence")
def recurrence(payload:MultiCycleRecurrenceRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).score_multi_cycle_recurrence(payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/reclosure-comparison")
def comparison(payload:PriorReclosureComparisonRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).compare_reclosures(payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/cross-entity-propagation")
def propagation(payload:CrossEntityPropagationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).propagation(payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/regulator-follow-up-correlation")
def followup(payload:RegulatorFollowUpCorrelationRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).correlate_regulator_follow_up(payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/materiality")
def materiality(payload:EnterpriseMaterialityRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).materiality(payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/escalations")
def escalation(payload:SupervisoryEscalationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_escalation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/investigations")
def investigation(payload:SupervisoryInvestigationCreate,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _svc(db,i).create_investigation(i.principal.user_id,payload.model_dump())
@router.post("/regulatory-examination-reclosed-intervention-sustainability/human-challenge")
def challenge(payload:HumanChallengeRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).human_challenge(i.principal.user_id,payload.model_dump()))
@router.post("/regulatory-examination-reclosed-intervention-sustainability/governance-actions")
def action(payload:GovernanceActionRequest,request:Request,db:Session=Depends(get_db)):
    i=_identity(request); return _call(lambda:_svc(db,i).governance_action(i.principal.user_id,payload.model_dump()))
