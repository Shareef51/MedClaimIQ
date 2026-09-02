from __future__ import annotations

def run_regulatory_knowledge_watch(*, tenant_id: str, snapshot: list[dict]) -> dict:
    """Monitoring-only worker: flags stale/conflicting candidates; never publishes or changes authority."""
    stale = [x.get("canonical_key") for x in snapshot if x.get("freshness_days", 0) > x.get("max_freshness_days", 365)]
    conflicts = [x.get("canonical_key") for x in snapshot if x.get("conflict_candidate")]
    return {"tenant_id": tenant_id, "stale_candidates": stale, "conflict_candidates": conflicts, "recommendation_only": True, "publish_authority": False}
