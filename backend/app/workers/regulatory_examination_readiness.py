from __future__ import annotations
from datetime import datetime, timezone

def run_examination_readiness_watch(*, tenant_id: str, requests: list[dict], now: str | None = None) -> dict:
    """Monitoring-only worker. It may flag evidence/SLA gaps but cannot approve or transmit anything."""
    current = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
    overdue, incomplete, unowned = [], [], []
    for row in requests:
        due = row.get("due_at")
        if due and datetime.fromisoformat(str(due).replace("Z", "+00:00")) < current and row.get("status") not in {"submitted", "closed"}: overdue.append(row.get("request_id"))
        if not row.get("evidence_complete", False): incomplete.append(row.get("request_id"))
        if not row.get("owner_id"): unowned.append(row.get("request_id"))
    return {"tenant_id": tenant_id, "overdue_request_ids": overdue, "incomplete_evidence_request_ids": incomplete, "unowned_request_ids": unowned, "recommendation_only": True, "approval_authority": False, "transmit_authority": False}
