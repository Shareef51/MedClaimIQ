from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.db.base import Base
from app.domain.realtime import EventEnvelope, EventTopic
from app.domain.sla import (
    BusinessCalendarDefinition, ClockMode, SLAPolicyDefinition, SLARule,
    TimerStatus, TimerType,
)
from app.models.claims import ClaimModel
from app.models.mcp import MCPApprovalRequestModel
from app.models.realtime import RealtimeOutboxModel
from app.models.sla import SLAReviewQueueEntryModel, SLATimerEventModel, SLATimerModel
from app.models.tenancy import OrganizationModel, TenantModel
from app.services.sla import SLAService
from app.sla.calendar import BusinessCalendar
from app.sla.notifications import SLAMCPNotificationBridge


def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(
            tenant_id="tenant-a", slug="tenant-a", display_name="Tenant A",
            tenant_type="payer", status="active", data_region="local",
        ))
        db.add(OrganizationModel(
            organization_id="org-a", tenant_id="tenant-a", slug="org-a",
            display_name="Org A", organization_type="payer",
            external_identifiers={}, is_active=True,
        ))
        db.flush()
        db.add(ClaimModel(
            claim_id="claim-1", tenant_id="tenant-a", external_claim_ref="EXT-1",
            patient_subject_id="patient-1", provider_organization_id="org-a",
            payer_organization_id="org-a", claim_type="medical", status="submitted",
            status_version=1, total_amount=Decimal("10"), currency="USD",
            service_from=date(2026, 8, 1),
        ))
        db.commit()
    return f


def definition(*, timezone="America/New_York", claim_minutes=480):
    return SLAPolicyDefinition(
        policy_key="payer-standard",
        version=1,
        calendar=BusinessCalendarDefinition(
            timezone=timezone, working_weekdays=[0, 1, 2, 3, 4],
            business_start="09:00", business_end="17:00",
        ),
        rules=[
            SLARule(timer_type=TimerType.CLAIM_REVIEW, duration_minutes=claim_minutes,
                    clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[120, 30]),
            SLARule(timer_type=TimerType.MISSING_DOCUMENT, duration_minutes=480,
                    clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[60]),
            SLARule(timer_type=TimerType.HOSPITAL_VERIFICATION, duration_minutes=480,
                    clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[60]),
            SLARule(timer_type=TimerType.PROVIDER_VERIFICATION, duration_minutes=480,
                    clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[60]),
            SLARule(timer_type=TimerType.REVIEWER_ACTION, duration_minutes=240,
                    clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[60]),
            SLARule(timer_type=TimerType.APPEAL_SUBMISSION, duration_minutes=1440,
                    clock_mode=ClockMode.ELAPSED, warning_minutes_before_due=[120]),
        ],
    )


def seed_policy(db, start=datetime(2026, 8, 20, 12, 0, tzinfo=UTC)):
    return SLAService(db, "tenant-a").create_policy(
        definition=definition(), created_by_user_id=None, effective_from=start, activate=True,
    )


def test_business_calendar_skips_weekend_and_holiday():
    calendar = BusinessCalendar(
        definition().calendar,
        holidays={date(2026, 8, 24)},
    )
    # Fri 16:00 New York + 120 business minutes => Tue 10:00 local because Monday is a holiday.
    start = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    due = calendar.add_business_minutes(start, 120)
    assert due == datetime(2026, 8, 25, 14, 0, tzinfo=UTC)


def test_elapsed_clock_does_not_skip_weekend():
    calendar = BusinessCalendar(definition().calendar)
    rule = definition().rule(TimerType.APPEAL_SUBMISSION)
    start = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    schedule = calendar.schedule(start=start, rule=rule)
    assert schedule.due_at == start + timedelta(days=1)


def test_schedule_is_idempotent_and_persists_policy_version():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        one = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.CLAIM_REVIEW,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC),
            idempotency_key="event:evt-1:claim-review",
        )
        two = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.CLAIM_REVIEW,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC),
            idempotency_key="event:evt-1:claim-review",
        )
        db.commit()
        assert one.timer_id == two.timer_id
        assert one.policy_version == 1
        assert len(db.scalars(select(SLATimerModel)).all()) == 1


def test_event_driven_scheduling_uses_event_identity():
    f = factory()
    with f() as db:
        seed_policy(db)
        event = EventEnvelope(
            event_id="evt-submit", event_type="claim.submitted", tenant_id="tenant-a",
            claim_id="claim-1", aggregate_type="claim", aggregate_id="claim-1",
            occurred_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), producer="test",
        )
        svc = SLAService(db, "tenant-a")
        assert len(svc.handle_event(event)) == 1
        assert len(svc.handle_event(event)) == 1
        db.commit()
        rows = db.scalars(select(SLATimerModel)).all()
        assert len(rows) == 1 and rows[0].source_event_id == "evt-submit"


def test_mcp_evidence_request_starts_missing_document_timer():
    f = factory()
    with f() as db:
        seed_policy(db)
        event = EventEnvelope(
            event_id="evt-mcp", event_type="mcp.tool.invoked", tenant_id="tenant-a",
            claim_id="claim-1", aggregate_type="mcp_tool", aggregate_id="claim.request_evidence",
            occurred_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), producer="test",
            payload={"tool_name": "claim.request_evidence"},
        )
        SLAService(db, "tenant-a").handle_event(event); db.commit()
        row = db.scalar(select(SLATimerModel))
        assert row.timer_type == TimerType.MISSING_DOCUMENT.value


def test_warning_emits_append_only_sla_and_realtime_events():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        timer = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.CLAIM_REVIEW,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="warn-timer",
        )
        warning = datetime.fromisoformat(timer.warning_schedule[0]) + timedelta(seconds=1)
        assert svc.evaluate_timer(timer, now=warning) == "warning"
        db.commit()
        assert db.scalar(select(SLATimerEventModel).where(SLATimerEventModel.event_type == "warning")) is not None
        assert db.scalar(select(RealtimeOutboxModel).where(RealtimeOutboxModel.topic == EventTopic.SLA.value)) is not None


def test_breach_creates_human_review_queue_entry():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        timer = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.HOSPITAL_VERIFICATION,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="breach-timer",
        )
        assert svc.evaluate_timer(timer, now=timer.due_at + timedelta(minutes=1)) == "breached"
        q = svc.ensure_breach_queue_entry(timer); db.commit()
        assert timer.status == TimerStatus.BREACHED.value
        assert q.priority == "high" and q.reason_code == "sla_hospital_verification_breached"


def test_appeal_breach_is_critical():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        timer = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.APPEAL_SUBMISSION,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="appeal-timer",
        )
        svc.evaluate_timer(timer, now=timer.due_at + timedelta(seconds=1))
        q = svc.ensure_breach_queue_entry(timer)
        assert q.priority == "critical"


def test_breach_notification_uses_mcp_human_approval_gate():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        timer = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.CLAIM_REVIEW,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="notify-timer",
        )
        result = SLAMCPNotificationBridge(db, "tenant-a").request_breach_notification(timer)
        db.commit()
        approval = db.scalar(select(MCPApprovalRequestModel))
        assert result.status.value == "approval_required"
        assert approval is not None and approval.tool_name == "notification.claim_update"


def test_completion_event_closes_active_timer():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.HOSPITAL_VERIFICATION,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="hospital-timer",
        )
        event = EventEnvelope(
            event_id="evt-verified", event_type="healthcare.claim.cross_verified", tenant_id="tenant-a",
            claim_id="claim-1", aggregate_type="claim", aggregate_id="claim-1",
            occurred_at=datetime(2026, 8, 20, 14, 0, tzinfo=UTC), producer="test",
        )
        svc.handle_event(event); db.commit()
        row = db.scalar(select(SLATimerModel))
        assert row.status == TimerStatus.COMPLETED.value and row.next_action_at is None


def test_countdown_reports_overdue_state_without_client_clock_authority():
    f = factory()
    with f() as db:
        seed_policy(db)
        svc = SLAService(db, "tenant-a")
        timer = svc.schedule_timer(
            claim_id="claim-1", timer_type=TimerType.APPEAL_SUBMISSION,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="countdown-timer",
        )
        rows = svc.countdowns("claim-1", now=timer.due_at + timedelta(seconds=10))
        assert rows[0].overdue is True
        assert rows[0].seconds_remaining < 0
        assert rows[0].warning_level == "breached"


def test_sla_policy_rejects_warning_beyond_duration():
    with pytest.raises(ValueError):
        SLARule(
            timer_type=TimerType.CLAIM_REVIEW, duration_minutes=60,
            clock_mode=ClockMode.BUSINESS, warning_minutes_before_due=[60],
        )


def test_sla_migration_has_rls_and_immutable_audit_contracts():
    text = Path("alembic/versions/0016_sla_deadline_engine.py").read_text()
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "sla_review_queue_entries" in text and "sla_worker_failures" in text
    assert "medclaimiq_reject_immutable_change" in text


def test_sla_topic_bootstrap_is_explicit():
    assert "medclaimiq.sla.events.v1" in Path("../docker-compose.yml").read_text()
    assert EventTopic.SLA.value == "medclaimiq.sla.events.v1"


def test_worker_recovers_missed_warning_from_persisted_next_action():
    from app.workers.sla_timers import SLATimerWorker
    f = factory()
    with f() as db:
        seed_policy(db)
        timer = SLAService(db, "tenant-a").schedule_timer(
            claim_id="claim-1", timer_type=TimerType.CLAIM_REVIEW,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="recovery-timer",
        )
        first_warning = datetime.fromisoformat(timer.warning_schedule[0])
        db.commit()
    processed = SLATimerWorker(f).recover_overdue_tenant("tenant-a", now=first_warning + timedelta(seconds=1))
    assert processed == 1
    with f() as db:
        row = db.scalar(select(SLATimerModel).where(SLATimerModel.idempotency_key == "recovery-timer"))
        assert row.next_warning_index == 1
        assert db.scalar(select(SLATimerEventModel).where(SLATimerEventModel.event_type == "warning")) is not None


def test_worker_failure_is_hash_audited_and_retried(monkeypatch):
    from app.models.sla import SLAWorkerFailureModel
    from app.workers.sla_timers import SLATimerWorker
    f = factory()
    with f() as db:
        seed_policy(db)
        timer = SLAService(db, "tenant-a").schedule_timer(
            claim_id="claim-1", timer_type=TimerType.APPEAL_SUBMISSION,
            started_at=datetime(2026, 8, 20, 13, 0, tzinfo=UTC), idempotency_key="retry-timer",
        )
        due = timer.due_at
        db.commit()

    def fail_notification(*args, **kwargs):
        raise ConnectionError("synthetic MCP outage")

    monkeypatch.setattr(SLAMCPNotificationBridge, "request_breach_notification", fail_notification)
    assert SLATimerWorker(f).run_tenant_once("tenant-a", now=due + timedelta(seconds=1)) == 0
    with f() as db:
        failure = db.scalar(select(SLAWorkerFailureModel))
        timer = db.scalar(select(SLATimerModel).where(SLATimerModel.idempotency_key == "retry-timer"))
        assert failure is not None and len(failure.error_sha256) == 64
        assert timer.status == "scheduled"
        assert timer.next_action_at is not None
        persisted_next = timer.next_action_at if timer.next_action_at.tzinfo else timer.next_action_at.replace(tzinfo=UTC)
        assert persisted_next > due
