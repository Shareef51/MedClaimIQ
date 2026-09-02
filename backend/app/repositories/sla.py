from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.sla import (
    SLAHolidayModel, SLAPolicyModel, SLAReviewQueueEntryModel,
    SLATimerEventModel, SLATimerModel, SLAWorkerFailureModel,
)


class SLARepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def add_policy(self, row: SLAPolicyModel) -> SLAPolicyModel:
        if row.tenant_id != self.tenant_id:
            raise ValueError("SLA policy tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def list_policies(self) -> list[SLAPolicyModel]:
        return list(self.session.scalars(select(SLAPolicyModel).where(
            SLAPolicyModel.tenant_id == self.tenant_id,
        ).order_by(SLAPolicyModel.policy_key, SLAPolicyModel.version.desc())))

    def active_policy(self, *, at: datetime | None = None) -> SLAPolicyModel | None:
        at = at or datetime.now(timezone.utc)
        return self.session.scalar(select(SLAPolicyModel).where(
            SLAPolicyModel.tenant_id == self.tenant_id,
            SLAPolicyModel.is_active.is_(True),
            SLAPolicyModel.effective_from <= at,
            (SLAPolicyModel.effective_to.is_(None) | (SLAPolicyModel.effective_to > at)),
        ).order_by(SLAPolicyModel.version.desc()).limit(1))

    def get_policy(self, policy_id: str, *, for_update: bool = False) -> SLAPolicyModel | None:
        stmt = select(SLAPolicyModel).where(SLAPolicyModel.tenant_id == self.tenant_id, SLAPolicyModel.policy_id == policy_id)
        if for_update: stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def deactivate_active_policies(self, *, except_policy_id: str, effective_to: datetime) -> None:
        for row in self.session.scalars(select(SLAPolicyModel).where(
            SLAPolicyModel.tenant_id == self.tenant_id,
            SLAPolicyModel.is_active.is_(True),
            SLAPolicyModel.policy_id != except_policy_id,
        )).all():
            row.is_active = False
            row.effective_to = effective_to

    def holidays(self, calendar_key: str) -> set[date]:
        return set(self.session.scalars(select(SLAHolidayModel.holiday_date).where(
            SLAHolidayModel.tenant_id == self.tenant_id,
            SLAHolidayModel.calendar_key == calendar_key,
        )))

    def add_holiday(self, row: SLAHolidayModel) -> SLAHolidayModel:
        if row.tenant_id != self.tenant_id: raise ValueError("holiday tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def timer_by_idempotency(self, key: str) -> SLATimerModel | None:
        return self.session.scalar(select(SLATimerModel).where(
            SLATimerModel.tenant_id == self.tenant_id, SLATimerModel.idempotency_key == key,
        ))

    def get_timer(self, timer_id: str, *, for_update: bool = False) -> SLATimerModel | None:
        stmt = select(SLATimerModel).where(SLATimerModel.tenant_id == self.tenant_id, SLATimerModel.timer_id == timer_id)
        if for_update: stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def add_timer(self, row: SLATimerModel) -> SLATimerModel:
        if row.tenant_id != self.tenant_id: raise ValueError("timer tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def list_claim_timers(self, claim_id: str, *, include_terminal: bool = True) -> list[SLATimerModel]:
        stmt = select(SLATimerModel).where(SLATimerModel.tenant_id == self.tenant_id, SLATimerModel.claim_id == claim_id)
        if not include_terminal:
            stmt = stmt.where(SLATimerModel.status.in_(["scheduled", "paused"]))
        return list(self.session.scalars(stmt.order_by(SLATimerModel.due_at)))

    def due_timers(self, now: datetime, *, limit: int = 100) -> list[SLATimerModel]:
        stmt = select(SLATimerModel).where(
            SLATimerModel.tenant_id == self.tenant_id,
            SLATimerModel.status == "scheduled",
            SLATimerModel.next_action_at.is_not(None),
            SLATimerModel.next_action_at <= now,
        ).order_by(SLATimerModel.next_action_at).limit(max(1, min(limit, 500))).with_for_update(skip_locked=True)
        return list(self.session.scalars(stmt))

    def add_event(self, row: SLATimerEventModel) -> SLATimerEventModel:
        if row.tenant_id != self.tenant_id: raise ValueError("SLA event tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def add_queue_entry(self, row: SLAReviewQueueEntryModel) -> SLAReviewQueueEntryModel:
        if row.tenant_id != self.tenant_id: raise ValueError("review queue tenant mismatch")
        self.session.add(row); self.session.flush(); return row

    def queue_for_timer(self, timer_id: str, level: str) -> SLAReviewQueueEntryModel | None:
        return self.session.scalar(select(SLAReviewQueueEntryModel).where(
            SLAReviewQueueEntryModel.tenant_id == self.tenant_id,
            SLAReviewQueueEntryModel.timer_id == timer_id,
            SLAReviewQueueEntryModel.escalation_level == level,
        ))

    def list_queue(self, *, claim_id: str | None = None, status: str = "open", limit: int = 200) -> list[SLAReviewQueueEntryModel]:
        stmt = select(SLAReviewQueueEntryModel).where(
            SLAReviewQueueEntryModel.tenant_id == self.tenant_id,
            SLAReviewQueueEntryModel.status == status,
        )
        if claim_id: stmt = stmt.where(SLAReviewQueueEntryModel.claim_id == claim_id)
        return list(self.session.scalars(stmt.order_by(SLAReviewQueueEntryModel.created_at).limit(max(1,min(limit,500)))))

    def add_failure(self, row: SLAWorkerFailureModel) -> SLAWorkerFailureModel:
        if row.tenant_id != self.tenant_id: raise ValueError("SLA failure tenant mismatch")
        self.session.add(row); self.session.flush(); return row
