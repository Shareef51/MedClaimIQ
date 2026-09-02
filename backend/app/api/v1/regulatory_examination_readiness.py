from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_examination_readiness import examination_readiness_contract
from app.schemas.regulatory_examination_readiness import *
from app.services.regulatory_examination_readiness import RegulatoryExaminationReadinessService

router = APIRouter(tags=["regulatory-examination-readiness"])

def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None: raise HTTPException(401, "authenticated identity unavailable")
    return identity

def _svc(db, i): return RegulatoryExaminationReadinessService(db, i.principal.tenant_id)

@router.get("/regulatory-examination-readiness/model")
def model(): return examination_readiness_contract()

@router.post("/regulatory-examination-readiness/examinations")
def create_scope(payload: ExaminationScopeRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).create_scope(i.principal.user_id, payload.model_dump())

@router.post("/regulatory-examination-readiness/requests")
def create_request(payload: RegulatorRequestCreate, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).create_regulator_request(i.principal.user_id, payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e

@router.post("/regulatory-examination-readiness/evidence")
def map_evidence(payload: EvidenceMapRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).map_evidence(i.principal.user_id, payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e

@router.get("/regulatory-examination-readiness/requests/{request_id}/evidence-quality")
def evidence_quality(request_id: str, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).evidence_quality(request_id)

@router.post("/regulatory-examination-readiness/drafts")
def create_draft(payload: ResponseDraftRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).create_draft(i.principal.user_id, payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e

@router.post("/regulatory-examination-readiness/requests/{request_id}/draft-decision")
def decide_draft(request_id: str, payload: HumanResponseDecision, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).decide_draft(i.principal.user_id, request_id, **payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e
    except ValueError as e: raise HTTPException(409, str(e)) from e

@router.post("/regulatory-examination-readiness/readiness")
def readiness(payload: ReadinessAssessmentRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).readiness(payload.model_dump())

@router.post("/regulatory-examination-readiness/packages")
def package(payload: EvidenceRoomPackageRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).build_package(i.principal.user_id, payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e
    except PermissionError as e: raise HTTPException(409, str(e)) from e

@router.post("/regulatory-examination-readiness/examinations/{examination_id}/package-decision")
def package_decision(examination_id: str, payload: SubmissionPackageDecision, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).decide_package(i.principal.user_id, examination_id, **payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e
    except ValueError as e: raise HTTPException(409, str(e)) from e
