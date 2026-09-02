from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.realtime import EventEnvelope, EventTopic
from app.domain.sla import (
    BusinessCalendarDefinition, EscalationPriority, ClockMode, SLAEventType,
    SLAPolicyDefinition, SLARule, SLACountdown, TimerStatus, TimerType,
)
from app.models.claims import ClaimModel
from app.models.sla import (
    SLAHolidayModel, SLAPolicyModel, SLAReviewQueueEntryModel, SLATimerEventModel,
    SLATimerModel, SLAWorkerFailureModel,
)
from app.repositories.sla import SLARepository
from app.realtime.events import enqueue_realtime_event
from app.sla.calendar import BusinessCalendar


EVENT_START_RULES: dict[str, tuple[TimerType, ...]] = {
    "claim.submitted": (TimerType.CLAIM_REVIEW,),
    "claim.missing_evidence.requested": (TimerType.MISSING_DOCUMENT,),
    "healthcare.verification.requested": (TimerType.HOSPITAL_VERIFICATION,),
    "provider.verification.requested": (TimerType.PROVIDER_VERIFICATION,),
    "claim.human_review.started": (TimerType.REVIEWER_ACTION,),
    "claim.appeal_ready": (TimerType.APPEAL_SUBMISSION,),
}
EVENT_COMPLETE_RULES: dict[str, tuple[TimerType, ...]] = {
    "claim.human_review.completed": (TimerType.CLAIM_REVIEW, TimerType.REVIEWER_ACTION),
    "claim.missing_evidence.received": (TimerType.MISSING_DOCUMENT,),
    "healthcare.claim.cross_verified": (TimerType.HOSPITAL_VERIFICATION,),
    "provider.verification.completed": (TimerType.PROVIDER_VERIFICATION,),
    "claim.appeal.submitted": (TimerType.APPEAL_SUBMISSION,),
    "claim.closed": tuple(TimerType),
}


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class SLAService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = SLARepository(session, tenant_id)

    def create_policy(self, *, definition: SLAPolicyDefinition, created_by_user_id: str | None,
                      effective_from: datetime, activate: bool = False) -> SLAPolicyModel:
        now = datetime.now(timezone.utc)
        effective = _aware(effective_from)
        row = SLAPolicyModel(
            policy_id=f"slapol_{uuid4().hex}", tenant_id=self.tenant_id,
            policy_key=definition.policy_key, version=definition.version,
            timezone=definition.calendar.timezone,
            calendar_definition=definition.calendar.model_dump(mode="json"),
            rules=[rule.model_dump(mode="json") for rule in definition.rules],
            is_active=activate, effective_from=effective, effective_to=None,
            created_by_user_id=created_by_user_id, created_at=now, updated_at=now,
        )
        self.repo.add_policy(row)
        if activate:
            self.repo.deactivate_active_policies(except_policy_id=row.policy_id, effective_to=effective)
        return row

    def activate_policy(self, policy_id: str, *, effective_at: datetime | None = None) -> SLAPolicyModel:
        now = _aware(effective_at or datetime.now(timezone.utc))
        row = self.repo.get_policy(policy_id, for_update=True)
        if row is None: raise LookupError("SLA policy was not found")
        self.repo.deactivate_active_policies(except_policy_id=policy_id, effective_to=now)
        row.is_active = True; row.effective_from = now; row.effective_to = None
        self.session.flush(); return row

    def add_holiday(self, *, calendar_key: str, holiday_date: date, name: str) -> SLAHolidayModel:
        row = SLAHolidayModel(
            holiday_id=f"slahol_{uuid4().hex}", tenant_id=self.tenant_id,
            calendar_key=calendar_key, holiday_date=holiday_date, name=name,
            created_at=datetime.now(timezone.utc),
        )
        return self.repo.add_holiday(row)

    def _definition(self, policy: SLAPolicyModel) -> SLAPolicyDefinition:
        return SLAPolicyDefinition(
            policy_key=policy.policy_key, version=policy.version,
            calendar=BusinessCalendarDefinition.model_validate(policy.calendar_definition),
            rules=[SLARule.model_validate(item) for item in policy.rules],
        )

    def schedule_timer(self, *, claim_id: str, timer_type: TimerType, started_at: datetime,
                       idempotency_key: str, source_event_id: str | None = None,
                       source_event_type: str | None = None, trace_id: str | None = None) -> SLATimerModel:
        existing = self.repo.timer_by_idempotency(idempotency_key)
        if existing is not None: return existing
        claim = self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id == self.tenant_id, ClaimModel.claim_id == claim_id))
        if claim is None: raise LookupError("claim was not found")
        policy = self.repo.active_policy(at=_aware(started_at))
        if policy is None: raise RuntimeError("tenant has no active SLA policy")
        definition = self._definition(policy); rule = definition.rule(timer_type)
        holidays = self.repo.holidays(definition.policy_key)
        calendar = BusinessCalendar(definition.calendar, holidays)
        schedule = calendar.schedule(start=_aware(started_at), rule=rule)
        now = datetime.now(timezone.utc)
        timer = SLATimerModel(
            timer_id=f"slatmr_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
            policy_id=policy.policy_id, policy_version=policy.version, timer_type=timer_type.value,
            clock_mode=rule.clock_mode.value, timezone=definition.calendar.timezone,
            status=TimerStatus.SCHEDULED.value, started_at=schedule.started_at, due_at=schedule.due_at,
            warning_schedule=[item.isoformat() for item in schedule.warning_schedule], next_warning_index=0,
            next_action_at=schedule.next_action_at, source_event_id=source_event_id,
            source_event_type=source_event_type, idempotency_key=idempotency_key,
            attempt_count=0, trace_id=trace_id, created_at=now, updated_at=now,
        )
        self.repo.add_timer(timer)
        self._event(timer, SLAEventType.SCHEDULED, f"{timer.timer_id}:scheduled", {
            "due_at": timer.due_at.isoformat(), "timezone": timer.timezone,
            "policy_version": timer.policy_version,
        })
        return timer

    def complete_timer_type(self, *, claim_id: str, timer_type: TimerType, completed_at: datetime,
                            reason: str, source_event_id: str | None = None) -> int:
        count = 0
        now = _aware(completed_at)
        for timer in self.repo.list_claim_timers(claim_id, include_terminal=False):
            if timer.timer_type != timer_type.value or timer.status != TimerStatus.SCHEDULED.value: continue
            timer.status = TimerStatus.COMPLETED.value; timer.completed_at = now; timer.next_action_at = None
            self._event(timer, SLAEventType.COMPLETED, f"{source_event_id or timer.timer_id}:complete:{timer.timer_type}", {"reason": reason})
            count += 1
        self.session.flush(); return count

    def handle_event(self, envelope: EventEnvelope) -> list[str]:
        if envelope.tenant_id != self.tenant_id or not envelope.claim_id:
            return []
        scheduled: list[str] = []
        for timer_type in EVENT_START_RULES.get(envelope.event_type, ()): 
            timer = self.schedule_timer(
                claim_id=envelope.claim_id, timer_type=timer_type, started_at=envelope.occurred_at,
                idempotency_key=f"event:{envelope.event_id}:{timer_type.value}",
                source_event_id=envelope.event_id, source_event_type=envelope.event_type, trace_id=envelope.trace_id,
            )
            scheduled.append(timer.timer_id)
        # MCP evidence request events are translated into a missing-document timer without trusting arbitrary tool output.
        if envelope.event_type == "mcp.tool.invoked" and envelope.payload.get("tool_name") == "claim.request_evidence":
            timer = self.schedule_timer(
                claim_id=envelope.claim_id, timer_type=TimerType.MISSING_DOCUMENT, started_at=envelope.occurred_at,
                idempotency_key=f"event:{envelope.event_id}:{TimerType.MISSING_DOCUMENT.value}",
                source_event_id=envelope.event_id, source_event_type=envelope.event_type, trace_id=envelope.trace_id,
            ); scheduled.append(timer.timer_id)
        for timer_type in EVENT_COMPLETE_RULES.get(envelope.event_type, ()):
            self.complete_timer_type(
                claim_id=envelope.claim_id, timer_type=timer_type, completed_at=envelope.occurred_at,
                reason=envelope.event_type, source_event_id=envelope.event_id,
            )
        return scheduled

    def evaluate_timer(self, timer: SLATimerModel, *, now: datetime) -> str:
        now = _aware(now); timer.last_evaluated_at = now
        if timer.status != TimerStatus.SCHEDULED.value: return timer.status
        warnings = [datetime.fromisoformat(item) for item in timer.warning_schedule]
        warnings = [_aware(item) for item in warnings]
        emitted = False
        while timer.next_warning_index < len(warnings) and warnings[timer.next_warning_index] <= now and now < _aware(timer.due_at):
            idx = timer.next_warning_index
            self._event(timer, SLAEventType.WARNING, f"{timer.timer_id}:warning:{idx}", {
                "warning_index": idx, "due_at": timer.due_at.isoformat(),
                "minutes_remaining": max(0, int((_aware(timer.due_at)-now).total_seconds()//60)),
            })
            timer.next_warning_index += 1; emitted = True
        if now >= _aware(timer.due_at):
            timer.status = TimerStatus.BREACHED.value; timer.breached_at = now; timer.next_action_at = None
            self._event(timer, SLAEventType.BREACHED, f"{timer.timer_id}:breached", {
                "due_at": timer.due_at.isoformat(), "overdue_seconds": int((now-_aware(timer.due_at)).total_seconds()),
            })
            return TimerStatus.BREACHED.value
        timer.next_action_at = warnings[timer.next_warning_index] if timer.next_warning_index < len(warnings) else _aware(timer.due_at)
        self.session.flush()
        return "warning" if emitted else TimerStatus.SCHEDULED.value

    def ensure_breach_queue_entry(self, timer: SLATimerModel) -> SLAReviewQueueEntryModel:
        existing = self.repo.queue_for_timer(timer.timer_id, "breach")
        if existing is not None: return existing
        priority = EscalationPriority.CRITICAL if timer.timer_type == TimerType.APPEAL_SUBMISSION.value else EscalationPriority.HIGH
        now = datetime.now(timezone.utc)
        row = SLAReviewQueueEntryModel(
            queue_entry_id=f"slaq_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=timer.claim_id,
            timer_id=timer.timer_id, escalation_level="breach", priority=priority.value,
            reason_code=f"sla_{timer.timer_type}_breached", status="open", created_at=now, updated_at=now,
        )
        return self.repo.add_queue_entry(row)

    def countdowns(self, claim_id: str, *, now: datetime | None = None) -> list[SLACountdown]:
        now = _aware(now or datetime.now(timezone.utc)); result=[]
        for timer in self.repo.list_claim_timers(claim_id, include_terminal=False):
            due = _aware(timer.due_at); started = _aware(timer.started_at)
            total = max(1.0, (due-started).total_seconds()); elapsed=max(0.0,(now-started).total_seconds())
            remaining = int((due-now).total_seconds()); percent=min(1.0, elapsed/total)
            warning_level = "breached" if remaining < 0 else "critical" if percent >= .9 else "warning" if percent >= .75 else "normal"
            result.append(SLACountdown(
                timer_id=timer.timer_id, timer_type=TimerType(timer.timer_type), status=TimerStatus(timer.status),
                due_at=due, seconds_remaining=remaining, percent_elapsed=round(percent,4), warning_level=warning_level,
                timezone=timer.timezone, overdue=remaining < 0, metadata={"policy_version":timer.policy_version},
            ))
        return result

    def _event(self, timer: SLATimerModel, event_type: SLAEventType, idempotency_key: str, metadata: dict) -> SLATimerEventModel:
        now = datetime.now(timezone.utc)
        row = SLATimerEventModel(
            sla_event_id=f"slaevt_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=timer.claim_id,
            timer_id=timer.timer_id, event_type=event_type.value, timer_type=timer.timer_type,
            idempotency_key=idempotency_key, metadata_json=metadata, trace_id=timer.trace_id, occurred_at=now,
        )
        self.repo.add_event(row)
        enqueue_realtime_event(self.session, envelope=EventEnvelope(
            event_id=row.sla_event_id, event_type=f"sla.timer.{event_type.value}", event_version="1.0",
            tenant_id=self.tenant_id, claim_id=timer.claim_id, aggregate_type="sla_timer", aggregate_id=timer.timer_id,
            occurred_at=now, trace_id=timer.trace_id, correlation_id=timer.claim_id,
            causation_id=timer.source_event_id, producer="medclaimiq-sla-engine",
            payload={"timer_id":timer.timer_id,"timer_type":timer.timer_type,"status":timer.status,"due_at":timer.due_at.isoformat(),**metadata},
            metadata={"policy_id":timer.policy_id,"policy_version":timer.policy_version,"timezone":timer.timezone},
        ), topic=EventTopic.SLA.value)
        return row

    def record_worker_failure(self, timer: SLATimerModel, exc: Exception, *, retry_at: datetime | None) -> None:
        timer.attempt_count += 1
        timer.last_error_code = type(exc).__name__
        timer.last_error_sha256 = sha256(str(exc).encode()).hexdigest()
        timer.next_action_at = retry_at
        self.repo.add_failure(SLAWorkerFailureModel(
            failure_id=f"slafail_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=timer.claim_id,
            timer_id=timer.timer_id, attempt=timer.attempt_count, error_code=type(exc).__name__,
            error_sha256=timer.last_error_sha256, retry_at=retry_at, created_at=datetime.now(timezone.utc),
        ))
