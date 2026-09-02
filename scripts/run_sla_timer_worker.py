from __future__ import annotations

import argparse
import time

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.workers.sla_timers import SLATimerWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the persisted SLA timer worker for one tenant")
    parser.add_argument("tenant_id")
    args = parser.parse_args()
    settings = get_settings()
    worker = SLATimerWorker(get_session_factory(), settings=settings)
    # The authoritative schedule is PostgreSQL `next_action_at`; this loop only polls it.
    while True:
        worker.run_tenant_once(args.tenant_id)
        time.sleep(max(0.1, settings.sla_timer_poll_seconds))


if __name__ == "__main__":
    main()
