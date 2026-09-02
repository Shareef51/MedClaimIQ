from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.release_engineering import ReleaseEngineeringRepository
from app.services.release_engineering import ReleaseEngineeringService, release_engineering_model_contract

router = APIRouter(tags=["release-engineering"])


def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity required")
    return identity


@router.get("/release-engineering-model")
def model_contract() -> dict:
    return release_engineering_model_contract()


@router.get("/release-engineering/history")
def history(request: Request, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    identity = _identity(request)
    if identity.principal.role not in {UserRole.TENANT_ADMIN, UserRole.AUDITOR}:
        raise HTTPException(403, "release history access denied")
    return ReleaseEngineeringService(ReleaseEngineeringRepository(db, identity.principal.tenant_id)).history(min(max(limit, 1), 100))
