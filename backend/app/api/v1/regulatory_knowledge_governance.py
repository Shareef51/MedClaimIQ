from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.regulatory_knowledge_governance import knowledge_governance_contract
from app.schemas.regulatory_knowledge_governance import *
from app.services.regulatory_knowledge_governance import RegulatoryKnowledgeGovernanceService

router = APIRouter(tags=["regulatory-knowledge-governance"])

def _identity(request: Request):
    i = getattr(request.state, "identity", None)
    if i is None: raise HTTPException(401, "authenticated identity unavailable")
    return i

def _svc(db, i): return RegulatoryKnowledgeGovernanceService(db, i.principal.tenant_id)

@router.get("/regulatory-knowledge/model")
def model(): return knowledge_governance_contract()

@router.post("/regulatory-knowledge/nodes")
def create_node(payload: KnowledgeNodeRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).upsert_node(i.principal.user_id, payload.model_dump())
    except (ValueError, PermissionError) as e: raise HTTPException(400, str(e)) from e

@router.post("/regulatory-knowledge/edges")
def create_edge(payload: KnowledgeEdgeRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).add_edge(i.principal.user_id, payload.model_dump())

@router.post("/regulatory-knowledge/{canonical_key}/approval")
def approve(canonical_key: str, payload: KnowledgeApprovalRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request)
    try: return _svc(db, i).approve_knowledge(i.principal.user_id, canonical_key, **payload.model_dump())
    except LookupError as e: raise HTTPException(404, str(e)) from e
    except (ValueError, PermissionError) as e: raise HTTPException(409, str(e)) from e

@router.post("/regulatory-knowledge/examination-query")
def query(payload: ExaminationQueryRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).query_graph(**payload.model_dump())

@router.post("/regulatory-knowledge/readiness")
def readiness(payload: ReadinessAssessmentRequest, request: Request, db: Session = Depends(get_db)):
    i = _identity(request); return _svc(db, i).readiness(payload.model_dump())
