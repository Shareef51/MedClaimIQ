from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_lessons_learned import lessons_learned_contract
from app.schemas.regulatory_lessons_learned import *
from app.services.regulatory_lessons_learned import RegulatoryLessonsLearnedService
from app.services.review_workbench import ReviewConflictError, ReviewLockError

router = APIRouter(tags=["regulatory-lessons-learned"])

def _i(r):
    x = getattr(r.state, "identity", None)
    if x is None: raise HTTPException(401, "authenticated identity unavailable")
    return x

def _run(db, fn):
    try:
        r = fn(); db.commit(); return r
    except Exception as e:
        db.rollback()
        if isinstance(e, LookupError): raise HTTPException(404, str(e)) from e
        if isinstance(e, (ReviewConflictError, ReviewLockError)): raise HTTPException(409, str(e)) from e
        if isinstance(e, (ValueError, PermissionError)): raise HTTPException(400, str(e)) from e
        raise

def _svc(db, t): return RegulatoryLessonsLearnedService(db, t)

@router.get("/regulatory-lessons-learned/model")
def model(): return lessons_learned_contract()

@router.get("/regulatory-lessons-learned/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    i = _i(request); return _run(db, lambda: _svc(db, i.principal.tenant_id).dashboard(i.principal.user_id))

@router.post("/regulatory-lessons-learned")
def create_lesson(payload: LessonCreateRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).create_lesson(i.principal.user_id, **payload.model_dump()))
    return {"lesson_id": x.lesson_id, "version": x.version, "status": x.status}

@router.post("/regulatory-lessons-learned/feedback")
def feedback(payload: RegulatoryFeedbackRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).ingest_feedback(i.principal.user_id, **payload.model_dump()))
    return {"feedback_id": x.feedback_id, "themes": x.supervisory_themes}

@router.post("/regulatory-lessons-learned/improvements")
def propose(payload: ControlImprovementProposalRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).propose_improvement(i.principal.user_id, **payload.model_dump()))
    return {"proposal_id": x.proposal_id, "status": x.status, "human_approval_required": x.human_approval_required}

@router.post("/regulatory-lessons-learned/improvements/{proposal_id}/decision")
def decide(proposal_id: str, payload: HumanImprovementDecisionRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).decide_improvement(i.principal.user_id, proposal_id, **payload.model_dump()))
    return {"decision_id": x.decision_id, "decision": x.decision}

@router.post("/regulatory-lessons-learned/knowledge-promotions")
def promote(payload: KnowledgePromotionRequest, request: Request, db: Session = Depends(get_db)):
    i = _i(request); x = _run(db, lambda: _svc(db, i.principal.tenant_id).promote_knowledge(i.principal.user_id, **payload.model_dump()))
    return {"promotion_id": x.promotion_id, "status": x.status}
