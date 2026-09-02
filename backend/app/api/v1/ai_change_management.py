from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.ai_change_management import AIChangeManagementRepository
from app.schemas.ai_change_management import (
    ConfigSnapshotCreate, DriftCheckRequest, ExperimentAssignRequest, ExperimentCreate,
    ExperimentObservationCreate, PromotionCreate, PromotionDecision, RollbackRequest,
)
from app.services.ai_change_management import AIChangeManagementService, ai_change_management_model_contract

router = APIRouter(tags=["ai-change-management"])
ADMIN = {UserRole.TENANT_ADMIN}
READERS = {UserRole.TENANT_ADMIN, UserRole.AUDITOR}


def _identity(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(401, "authenticated identity required")
    return identity


def _service(request: Request, db: Session, roles: set[UserRole]):
    identity = _identity(request)
    if identity.principal.role not in roles:
        raise HTTPException(403, "AI configuration governance access denied")
    return identity, AIChangeManagementService(AIChangeManagementRepository(db, identity.principal.tenant_id))


def _call(db: Session, fn):
    try:
        result = fn()
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "configuration governance uniqueness conflict") from exc
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc)) from exc


@router.get("/ai-change-management-model")
def model_contract() -> dict:
    return ai_change_management_model_contract()


@router.get("/ai-configurations/history")
def history(request: Request, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, READERS)
    return svc.history(min(max(limit, 1), 100))


@router.post("/ai-configurations/snapshots")
def create_snapshot(payload: ConfigSnapshotCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.create_snapshot(actor=identity.principal.user_id, **payload.model_dump()))
    return {"snapshot_id": item.snapshot_id, "config_key": item.config_key, "version": item.version, "payload_sha256": item.payload_sha256}


@router.get("/ai-configurations/resolve")
def resolve(request: Request, environment: str = Query(...), config_key: str = Query(...), db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, READERS)
    resolved = svc.resolve(environment=environment, config_key=config_key)
    if not resolved: raise HTTPException(404, "configuration assignment not found")
    assignment, snapshot = resolved
    return {"environment": environment, "config_key": config_key, "snapshot_id": snapshot.snapshot_id,
            "version": snapshot.version, "configuration_type": snapshot.configuration_type,
            "payload": snapshot.payload, "payload_sha256": snapshot.payload_sha256,
            "assignment_version": assignment.assignment_version}


@router.post("/ai-configurations/promotions")
def promote(payload: PromotionCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.request_promotion(actor=identity.principal.user_id, **payload.model_dump()))
    return {"promotion_id": item.promotion_id, "risk": item.risk, "status": item.status, "target_environment": item.target_environment}


@router.post("/ai-configurations/promotions/{promotion_id}/decision")
def decide(promotion_id: str, payload: PromotionDecision, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.decide_promotion(actor=identity.principal.user_id, promotion_id=promotion_id, **payload.model_dump()))
    return {"promotion_id": item.promotion_id, "status": item.status, "approved_by": item.approved_by}


@router.post("/ai-configurations/rollback")
def rollback(payload: RollbackRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.rollback(actor=identity.principal.user_id, **payload.model_dump()))
    return {"assignment_id": item.assignment_id, "snapshot_id": item.snapshot_id, "assignment_version": item.assignment_version, "source": item.source}


@router.post("/ai-configurations/runtime-resolve")
def runtime_resolve(payload: ExperimentAssignRequest, request: Request, environment: str = Query(...), config_key: str = Query(...), experiment_id: str | None = Query(default=None), db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, ADMIN)
    return _call(db, lambda: svc.resolve_for_subject(environment=environment, config_key=config_key, experiment_id=experiment_id, subject_key=payload.subject_key if experiment_id else None))


@router.post("/ai-experiments")
def create_experiment(payload: ExperimentCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.create_experiment(actor=identity.principal.user_id, **payload.model_dump()))
    return {"experiment_id": item.experiment_id, "status": item.status, "mode": item.mode, "shadow_only": item.shadow_only}


@router.post("/ai-experiments/{experiment_id}/start")
def start_experiment(experiment_id: str, payload: PromotionDecision, request: Request, db: Session = Depends(get_db)) -> dict:
    if not payload.approve: raise HTTPException(409, "starting an experiment requires approval=true")
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.start_experiment(actor=identity.principal.user_id, experiment_id=experiment_id, approval_reason=payload.reason))
    return {"experiment_id": item.experiment_id, "status": item.status}


@router.post("/ai-experiments/{experiment_id}/assign")
def assign(experiment_id: str, payload: ExperimentAssignRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, READERS)
    item = _call(db, lambda: svc.assign_experiment(experiment_id=experiment_id, subject_key=payload.subject_key))
    return {"assignment_id": item.assignment_id, "bucket": item.bucket, "variant": item.variant, "snapshot_id": item.snapshot_id}


@router.post("/ai-experiments/{experiment_id}/complete")
def complete_experiment(experiment_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    return _call(db, lambda: svc.complete_experiment(actor=identity.principal.user_id, experiment_id=experiment_id))


@router.post("/ai-experiments/{experiment_id}/observations")
def observe(experiment_id: str, payload: ExperimentObservationCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.observe_experiment(experiment_id=experiment_id, **payload.model_dump()))
    return {"observation_id": item.observation_id}


@router.get("/ai-experiments/{experiment_id}/summary")
def experiment_summary(experiment_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    _, svc = _service(request, db, READERS)
    try: return svc.experiment_summary(experiment_id)
    except ValueError as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/ai-configurations/drift/check")
def drift_check(payload: DriftCheckRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identity, svc = _service(request, db, ADMIN)
    item = _call(db, lambda: svc.drift_check(actor=identity.principal.user_id, **payload.model_dump()))
    return {"drift_event_id": item.drift_event_id, "status": item.status, "expected_sha256": item.expected_sha256, "observed_sha256": item.observed_sha256}
