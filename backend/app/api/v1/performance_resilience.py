from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.performance_resilience import PerformanceResilienceRepository
from app.services.performance_resilience import PerformanceResilienceService, performance_resilience_model_contract

router = APIRouter(tags=["performance-resilience"])


def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity required")
    return identity


@router.get("/performance-resilience-model")
def model_contract() -> dict:
    return performance_resilience_model_contract()


@router.get("/performance-resilience/history")
def history(request: Request, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    identity = _identity(request)
    if identity.principal.role not in {UserRole.TENANT_ADMIN, UserRole.AUDITOR, UserRole.SYSTEM_ADMIN}:
        raise HTTPException(403, "performance/resilience history access denied")
    repo = PerformanceResilienceRepository(db, identity.principal.tenant_id)
    return PerformanceResilienceService(repo).history(min(max(limit, 1), 100))
