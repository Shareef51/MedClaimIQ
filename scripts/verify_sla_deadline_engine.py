from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/sla.py", "backend/app/sla/calendar.py", "backend/app/services/sla.py",
    "backend/app/workers/sla_timers.py", "backend/app/models/sla.py", "backend/app/api/v1/sla.py",
    "backend/alembic/versions/0016_sla_deadline_engine.py", "config/sla_deadline_policy.json",
    "docs/SLA_TIMER_DEADLINE_ESCALATION_ENGINE.md", "sample-data/sla_deadline_scenarios.json",
]
missing = [item for item in required if not (root / item).exists()]
if missing:
    raise SystemExit(f"missing SLA artifacts: {missing}")
text = (root / "backend/alembic/versions/0016_sla_deadline_engine.py").read_text()
for term in ("sla_timers", "sla_timer_events", "sla_review_queue_entries", "FORCE ROW LEVEL SECURITY", "medclaimiq_reject_immutable_change"):
    if term not in text:
        raise SystemExit(f"migration contract missing: {term}")
realtime = (root / "backend/app/domain/realtime.py").read_text()
if "medclaimiq.sla.events.v1" not in realtime:
    raise SystemExit("SLA topic missing")
print("SLA/deadline architecture verification passed")
