from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.db.session import get_db
from app.domain.access import Permission, ROLE_PERMISSIONS
from app.models.sla import SLAReviewQueueEntryModel, SLATimerEventModel, SLATimerModel
from app.schemas.sla import (
    CreateSLAPolicyRequest, ManualTimerRequest, SLAHolidayRequest,
    SLAPolicyResponse, SLAQueueItemResponse, SLATimerResponse,
)
from app.services.sla import SLAService

router = APIRouter(tags=["sla-deadlines"])


def _require(identity, permission: Permission) -> None:
    if permission not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403, detail=f"{permission.value} permission is required")


def _timer_response(row: SLATimerModel) -> SLATimerResponse:
    return SLATimerResponse(
        timer_id=row.timer_id, timer_type=row.timer_type, status=row.status,
        policy_version=row.policy_version, timezone=row.timezone,
        started_at=row.started_at, due_at=row.due_at, next_action_at=row.next_action_at,
        warning_schedule=list(row.warning_schedule or []), breached_at=row.breached_at,
    )


@router.get("/sla-model")
def sla_model():
    return {
        "clock": {"persistence": "UTC", "calculation": "tenant IANA timezone", "business_calendar": True},
        "timer_types": [
            "claim_review", "missing_document", "hospital_verification",
            "provider_verification", "reviewer_action", "appeal_submission",
        ],
        "durability": {
            "persisted_next_action_at": True, "restart_recovery": True,
            "event_idempotency": True, "worker_retry": "bounded exponential",
        },
        "escalation": {
            "human_review_queue": True, "sla_breach_events": True,
            "mcp_notification": "human-approval-gated", "automatic_claim_decision": False,
        },
        "realtime": {"topic": "medclaimiq.sla.events.v1", "countdown": "server deadline + client ticking"},
        "privacy": {"raw_patient_data_in_timer_events": False},
    }


@router.get("/sla/policies", response_model=list[SLAPolicyResponse])
def list_policies(request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    _require(identity, Permission.TENANT_SETTINGS_MANAGE)
    rows = SLAService(db, identity.principal.tenant_id).repo.list_policies()
    return [SLAPolicyResponse(
        policy_id=row.policy_id, policy_key=row.policy_key, version=row.version,
        timezone=row.timezone, is_active=row.is_active, effective_from=row.effective_from,
        effective_to=row.effective_to,
    ) for row in rows]


@router.post("/sla/policies", response_model=SLAPolicyResponse)
def create_policy(payload: CreateSLAPolicyRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _require(identity, Permission.TENANT_SETTINGS_MANAGE)
    try:
        row = SLAService(db, identity.principal.tenant_id).create_policy(
            definition=payload.definition(), created_by_user_id=identity.principal.user_id,
            effective_from=payload.effective_from, activate=payload.activate,
        )
        db.commit()
        return SLAPolicyResponse(
            policy_id=row.policy_id, policy_key=row.policy_key, version=row.version,
            timezone=row.timezone, is_active=row.is_active, effective_from=row.effective_from,
            effective_to=row.effective_to,
        )
    except (ValueError, RuntimeError) as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sla/policies/{policy_id}/activate", response_model=SLAPolicyResponse)
def activate_policy(policy_id: str, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _require(identity, Permission.TENANT_SETTINGS_MANAGE)
    try:
        row = SLAService(db, identity.principal.tenant_id).activate_policy(policy_id)
        db.commit()
        return SLAPolicyResponse(
            policy_id=row.policy_id, policy_key=row.policy_key, version=row.version,
            timezone=row.timezone, is_active=row.is_active, effective_from=row.effective_from,
            effective_to=row.effective_to,
        )
    except LookupError as exc:
        db.rollback(); raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sla/holidays")
def add_holiday(payload: SLAHolidayRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _require(identity, Permission.TENANT_SETTINGS_MANAGE)
    row = SLAService(db, identity.principal.tenant_id).add_holiday(
        calendar_key=payload.calendar_key, holiday_date=payload.holiday_date, name=payload.name,
    )
    db.commit()
    return {"holiday_id": row.holiday_id, "holiday_date": row.holiday_date, "calendar_key": row.calendar_key}


@router.get("/claims/{claim_id}/sla/timers", response_model=list[SLATimerResponse])
def list_claim_timers(claim_id: str, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _authorize_claim_read(db, identity, claim_id)
    return [_timer_response(row) for row in SLAService(db, identity.principal.tenant_id).repo.list_claim_timers(claim_id)]


@router.post("/claims/{claim_id}/sla/timers", response_model=SLATimerResponse)
def schedule_manual_timer(claim_id: str, payload: ManualTimerRequest, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _authorize_claim_read(db, identity, claim_id); _require(identity, Permission.CLAIM_REVIEW)
    try:
        row = SLAService(db, identity.principal.tenant_id).schedule_timer(
            claim_id=claim_id, timer_type=payload.timer_type, started_at=payload.started_at,
            idempotency_key=f"manual:{payload.idempotency_key}", trace_id=getattr(identity, "trace_id", None),
        )
        db.commit(); return _timer_response(row)
    except (LookupError, RuntimeError, ValueError) as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/claims/{claim_id}/sla/countdowns")
def countdowns(claim_id: str, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _authorize_claim_read(db, identity, claim_id)
    now = datetime.now(timezone.utc)
    rows = SLAService(db, identity.principal.tenant_id).countdowns(claim_id, now=now)
    return {"server_time": now, "claim_id": claim_id, "timers": [item.model_dump(mode="json") for item in rows]}


@router.get("/claims/{claim_id}/sla/review-queue", response_model=list[SLAQueueItemResponse])
def claim_review_queue(claim_id: str, request: Request, db: Session = Depends(get_db)):
    identity = _identity(request); _authorize_claim_read(db, identity, claim_id); _require(identity, Permission.CLAIM_REVIEW)
    rows = SLAService(db, identity.principal.tenant_id).repo.list_queue(claim_id=claim_id)
    return [SLAQueueItemResponse(
        queue_entry_id=row.queue_entry_id, claim_id=row.claim_id, timer_id=row.timer_id,
        priority=row.priority, reason_code=row.reason_code, status=row.status,
        mcp_approval_id=row.mcp_approval_id, created_at=row.created_at,
    ) for row in rows]


@router.get("/sla/operations")
def sla_operations(request: Request, db: Session = Depends(get_db)):
    identity = _identity(request)
    permissions = ROLE_PERMISSIONS[identity.principal.role]
    if Permission.SYSTEM_HEALTH_READ not in permissions and Permission.AUDIT_READ not in permissions:
        raise HTTPException(status_code=403, detail="system health or audit permission required")
    tenant = identity.principal.tenant_id
    timers = dict(db.execute(select(SLATimerModel.status, func.count()).where(
        SLATimerModel.tenant_id == tenant,
    ).group_by(SLATimerModel.status)).all())
    queue_open = db.scalar(select(func.count()).select_from(SLAReviewQueueEntryModel).where(
        SLAReviewQueueEntryModel.tenant_id == tenant, SLAReviewQueueEntryModel.status == "open",
    )) or 0
    events = db.scalar(select(func.count()).select_from(SLATimerEventModel).where(SLATimerEventModel.tenant_id == tenant)) or 0
    return {"timers_by_status": timers, "open_review_queue_entries": queue_open, "timer_events": events}
