from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.db.session import get_session_factory
from app.workers.sla_timers import SLATimerWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Process persisted MedClaimIQ SLA timers for one tenant")
    parser.add_argument("tenant_id")
    parser.add_argument("--recovery", action="store_true", help="use the larger restart-recovery batch")
    args = parser.parse_args()
    worker = SLATimerWorker(get_session_factory())
    now = datetime.now(timezone.utc)
    count = worker.recover_overdue_tenant(args.tenant_id, now=now) if args.recovery else worker.run_tenant_once(args.tenant_id, now=now)
    print({"tenant_id": args.tenant_id, "processed": count, "evaluated_at": now.isoformat()})


if __name__ == "__main__":
    main()
