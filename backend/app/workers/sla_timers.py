from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.models.sla import SLAPolicyModel, SLATimerModel
from app.services.sla import SLAService
from app.sla.notifications import SLAMCPNotificationBridge


class SLATimerWorker:
    """Restart-safe timer evaluator.

    The worker does not rely on in-memory sleeps. It queries persisted `next_action_at`
    rows, which means deadlines survive process restarts and broker outages.
    """

    def __init__(self, session_factory, *, settings: Settings | None = None) -> None:
        self.session_factory = session_factory
        self.settings = settings or get_settings()

    def run_tenant_once(self, tenant_id: str, *, now: datetime | None = None, limit: int | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        processed = 0
        with self.session_factory() as db:
            service = SLAService(db, tenant_id)
            timers = service.repo.due_timers(now, limit=limit or self.settings.sla_worker_batch_size)
            for timer in timers:
                try:
                    result = service.evaluate_timer(timer, now=now)
                    if result == "breached":
                        queue = service.ensure_breach_queue_entry(timer)
                        if queue.mcp_approval_id is None:
                            mcp = SLAMCPNotificationBridge(
                                db, tenant_id, approval_ttl_minutes=self.settings.mcp_approval_ttl_minutes,
                            ).request_breach_notification(timer)
                            queue.mcp_approval_id = mcp.approval_id
                    timer.attempt_count = 0
                    timer.last_error_code = None
                    timer.last_error_sha256 = None
                    processed += 1
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    # Reload under a fresh transaction so failure bookkeeping itself is durable.
                    timer = SLAService(db, tenant_id).repo.get_timer(timer.timer_id, for_update=True)
                    if timer is not None:
                        attempt = timer.attempt_count + 1
                        retry = None
                        if attempt < self.settings.sla_worker_max_attempts:
                            delay = min(
                                self.settings.sla_worker_retry_max_seconds,
                                self.settings.sla_worker_retry_base_seconds * (2 ** max(0, attempt - 1)),
                            )
                            retry = now + timedelta(seconds=delay)
                        SLAService(db, tenant_id).record_worker_failure(timer, exc, retry_at=retry)
                        db.commit()
            return processed

    def recover_overdue_tenant(self, tenant_id: str, *, now: datetime | None = None) -> int:
        """Processes timers that became due while workers were down."""
        return self.run_tenant_once(tenant_id, now=now, limit=self.settings.sla_worker_recovery_batch_size)
