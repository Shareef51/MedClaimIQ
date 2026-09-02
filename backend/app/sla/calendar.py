from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.sla import BusinessCalendarDefinition, ClockMode, SLARule, TimerScheduleResult


class BusinessCalendarError(ValueError):
    pass


class BusinessCalendar:
    """Tenant-local business clock with UTC persistence boundaries.

    Calculations are done in the configured IANA timezone. Persisted timestamps are
    always returned as timezone-aware UTC values.
    """

    def __init__(self, definition: BusinessCalendarDefinition, holidays: set[date] | None = None) -> None:
        self.definition = definition
        self.holidays = holidays or set()
        try:
            self.zone = ZoneInfo(definition.timezone)
        except ZoneInfoNotFoundError as exc:
            raise BusinessCalendarError(f"unknown IANA timezone: {definition.timezone}") from exc
        self.start_time = time.fromisoformat(definition.business_start)
        self.end_time = time.fromisoformat(definition.business_end)
        if self.end_time <= self.start_time:
            raise BusinessCalendarError("business_end must be later than business_start")
        self.weekdays = frozenset(definition.working_weekdays)

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise BusinessCalendarError("SLA timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    def is_business_day(self, day: date) -> bool:
        return day.weekday() in self.weekdays and day not in self.holidays

    def _window(self, day: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(day, self.start_time, tzinfo=self.zone),
            datetime.combine(day, self.end_time, tzinfo=self.zone),
        )

    def next_business_instant(self, value: datetime) -> datetime:
        local = self._aware_utc(value).astimezone(self.zone)
        day = local.date()
        for _ in range(370):
            if self.is_business_day(day):
                start, end = self._window(day)
                if local <= start:
                    return start.astimezone(timezone.utc)
                if start <= local < end:
                    return local.astimezone(timezone.utc)
            day += timedelta(days=1)
            local = datetime.combine(day, time.min, tzinfo=self.zone)
        raise BusinessCalendarError("could not find a business day within one year")

    def add_business_minutes(self, start: datetime, minutes: int) -> datetime:
        if minutes < 0:
            raise BusinessCalendarError("business duration cannot be negative")
        cursor = self.next_business_instant(start).astimezone(self.zone)
        remaining = minutes
        while remaining > 0:
            day = cursor.date()
            if not self.is_business_day(day):
                cursor = self.next_business_instant(cursor).astimezone(self.zone)
                continue
            _, end = self._window(day)
            available = max(0, int((end - cursor).total_seconds() // 60))
            if remaining <= available:
                return (cursor + timedelta(minutes=remaining)).astimezone(timezone.utc)
            remaining -= available
            cursor = self.next_business_instant(end + timedelta(microseconds=1)).astimezone(self.zone)
        return cursor.astimezone(timezone.utc)

    def subtract_business_minutes(self, end: datetime, minutes: int) -> datetime:
        if minutes < 0:
            raise BusinessCalendarError("business duration cannot be negative")
        cursor = self._aware_utc(end).astimezone(self.zone)
        remaining = minutes
        # Warning calculation is bounded by the rule duration and intended for a small number of offsets.
        while remaining > 0:
            day = cursor.date()
            if not self.is_business_day(day):
                day -= timedelta(days=1)
                while not self.is_business_day(day):
                    day -= timedelta(days=1)
                _, business_end = self._window(day)
                cursor = business_end
                continue
            start, business_end = self._window(day)
            if cursor > business_end:
                cursor = business_end
            if cursor <= start:
                day -= timedelta(days=1)
                while not self.is_business_day(day):
                    day -= timedelta(days=1)
                _, cursor = self._window(day)
                continue
            available = max(0, int((cursor - start).total_seconds() // 60))
            if remaining <= available:
                return (cursor - timedelta(minutes=remaining)).astimezone(timezone.utc)
            remaining -= available
            day -= timedelta(days=1)
            while not self.is_business_day(day):
                day -= timedelta(days=1)
            _, cursor = self._window(day)
        return cursor.astimezone(timezone.utc)

    def schedule(self, *, start: datetime, rule: SLARule) -> TimerScheduleResult:
        started = self._aware_utc(start)
        if rule.clock_mode is ClockMode.BUSINESS:
            effective_start = self.next_business_instant(started)
            due = self.add_business_minutes(effective_start, rule.duration_minutes)
            warnings = [self.subtract_business_minutes(due, offset) for offset in rule.warning_minutes_before_due]
        else:
            effective_start = started
            due = started + timedelta(minutes=rule.duration_minutes)
            warnings = [due - timedelta(minutes=offset) for offset in rule.warning_minutes_before_due]
        warnings = sorted({item for item in warnings if item > effective_start})
        next_action = warnings[0] if warnings else due
        return TimerScheduleResult(
            started_at=effective_start,
            due_at=due,
            warning_schedule=warnings,
            next_action_at=next_action,
        )
