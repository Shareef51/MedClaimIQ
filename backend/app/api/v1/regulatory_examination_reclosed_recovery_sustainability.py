from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_reclosed_recovery_sustainability import reclosed_recovery_sustainability_contract
from app.schemas.regulatory_examination_reclosed_recovery_sustainability import *
from app.services.regulatory_examination_reclosed_recovery_sustainability import RegulatoryExaminationReclosedRecoverySustainabilityService
router=APIRouter(tags=["regulatory-examination-reclosed-recovery-sustainability"])
def _identity(request):
    i=getattr(request.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return RegulatoryExaminationReclosedRecoverySustainabilityService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get("/regulatory-examination-reclosed-recovery-sustainability/model")
def model(): return reclosed_recovery_sustainability_contract()
@router.post("/regulatory-examination-reclosed-recovery-sustainability/recovery-decay")
def decay(p:RecoveryDecayRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).decay(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/multi-cycle-recurrence")
def recurrence(p:MultiCycleRecurrenceRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).recurrence(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/risk-rebound")
def rebound(p:RiskReboundRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).rebound(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/reclosure-comparison")
def compare(p:ReclosureComparisonRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).compare(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/regulator-followups")
def regulator(p:RegulatorFollowupCorrelationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).regulator(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/enterprise-materiality")
def materiality(p:EnterpriseMaterialityRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _svc(db,i).materiality(p.model_dump())
@router.post("/regulatory-examination-reclosed-recovery-sustainability/investigations")
def investigate(p:SupervisoryInvestigationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).open_investigation(i.principal.user_id,p.model_dump()))
@router.post("/regulatory-examination-reclosed-recovery-sustainability/escalations")
def escalate(p:SupervisoryEscalationRequest,request:Request,db:Session=Depends(get_db)): i=_identity(request); return _call(lambda:_svc(db,i).escalate(i.principal.user_id,p.model_dump()))
