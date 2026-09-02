from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sla import BusinessCalendarDefinition, SLAPolicyDefinition, SLARule, TimerType


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSLAPolicyRequest(_StrictModel):
    policy_key: str = Field(min_length=3, max_length=120)
    version: int = Field(ge=1)
    calendar: BusinessCalendarDefinition
    rules: list[SLARule] = Field(min_length=1)
    effective_from: datetime
    activate: bool = False

    def definition(self) -> SLAPolicyDefinition:
        return SLAPolicyDefinition(policy_key=self.policy_key, version=self.version, calendar=self.calendar, rules=self.rules)


class SLAHolidayRequest(_StrictModel):
    calendar_key: str = Field(min_length=3, max_length=120)
    holiday_date: date
    name: str = Field(min_length=2, max_length=160)


class ManualTimerRequest(_StrictModel):
    timer_type: TimerType
    started_at: datetime
    idempotency_key: str = Field(min_length=8, max_length=180)


class SLAPolicyResponse(_StrictModel):
    policy_id: str
    policy_key: str
    version: int
    timezone: str
    is_active: bool
    effective_from: datetime
    effective_to: datetime | None = None


class SLATimerResponse(_StrictModel):
    timer_id: str
    timer_type: str
    status: str
    policy_version: int
    timezone: str
    started_at: datetime
    due_at: datetime
    next_action_at: datetime | None = None
    warning_schedule: list[str]
    breached_at: datetime | None = None


class SLAQueueItemResponse(_StrictModel):
    queue_entry_id: str
    claim_id: str
    timer_id: str
    priority: str
    reason_code: str
    status: str
    mcp_approval_id: str | None = None
    created_at: datetime
