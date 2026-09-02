from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TimerType(StrEnum):
    CLAIM_REVIEW = "claim_review"
    MISSING_DOCUMENT = "missing_document"
    HOSPITAL_VERIFICATION = "hospital_verification"
    PROVIDER_VERIFICATION = "provider_verification"
    REVIEWER_ACTION = "reviewer_action"
    APPEAL_SUBMISSION = "appeal_submission"


class TimerStatus(StrEnum):
    SCHEDULED = "scheduled"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BREACHED = "breached"


class ClockMode(StrEnum):
    ELAPSED = "elapsed"
    BUSINESS = "business"


class SLAEventType(StrEnum):
    SCHEDULED = "scheduled"
    WARNING = "warning"
    BREACHED = "breached"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RESUMED = "resumed"
    RECOVERED = "recovered"
    NOTIFICATION_APPROVAL_REQUESTED = "notification_approval_requested"
    NOTIFICATION_SENT = "notification_sent"


class EscalationPriority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SLARule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timer_type: TimerType
    duration_minutes: int = Field(ge=1, le=60 * 24 * 365)
    clock_mode: ClockMode = ClockMode.BUSINESS
    warning_minutes_before_due: list[int] = Field(default_factory=list, max_length=8)
    escalate_on_breach: bool = True
    notification_on_breach: bool = True

    @field_validator("warning_minutes_before_due")
    @classmethod
    def validate_warnings(cls, value: list[int], info):
        cleaned = sorted(set(value), reverse=True)
        if any(item <= 0 for item in cleaned):
            raise ValueError("warning offsets must be positive minutes")
        duration = info.data.get("duration_minutes")
        if duration is not None and any(item >= duration for item in cleaned):
            raise ValueError("warning offsets must be less than the SLA duration")
        return cleaned


class BusinessCalendarDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str = Field(min_length=1, max_length=80)
    working_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7)
    business_start: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    business_end: str = Field(default="17:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @field_validator("working_weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]):
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("working weekdays must be between 0 and 6")
        return sorted(set(value))


class SLAPolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy_key: str = Field(min_length=3, max_length=120)
    version: int = Field(ge=1)
    calendar: BusinessCalendarDefinition
    rules: list[SLARule] = Field(min_length=1)

    @field_validator("rules")
    @classmethod
    def unique_rules(cls, value: list[SLARule]):
        kinds = [item.timer_type for item in value]
        if len(kinds) != len(set(kinds)):
            raise ValueError("only one rule per timer type is allowed")
        return value

    def rule(self, timer_type: TimerType) -> SLARule:
        for rule in self.rules:
            if rule.timer_type is timer_type:
                return rule
        raise KeyError(f"SLA policy has no rule for {timer_type.value}")


class TimerScheduleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    started_at: datetime
    due_at: datetime
    warning_schedule: list[datetime]
    next_action_at: datetime


class SLACountdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timer_id: str
    timer_type: TimerType
    status: TimerStatus
    due_at: datetime
    seconds_remaining: int
    percent_elapsed: float = Field(ge=0.0)
    warning_level: str
    timezone: str
    overdue: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
