from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def evidence_sufficiency(required_types: list[str], evidence: list[dict]) -> dict:
    active = {e.get("evidence_type") for e in evidence if e.get("status", "active") == "active" and len(e.get("sha256", "")) == 64}
    missing = sorted(set(required_types) - active)
    stale = [e.get("evidence_id") for e in evidence if e.get("stale") is True]
    return {"sufficient": not missing and not stale, "missing_types": missing, "stale_evidence_ids": stale}


def closure_readiness(commitment: dict, milestones: list[dict], evidence: list[dict], validations: list[dict], dependencies: list[dict], follow_ups: list[dict], entity_checks: list[dict]) -> dict:
    blockers = []
    if not milestones or any(m.get("status") != "completed" for m in milestones): blockers.append("milestones_incomplete")
    ev = evidence_sufficiency(commitment.get("required_evidence_types", []), evidence)
    if not ev["sufficient"]: blockers.append("evidence_insufficient")
    independent = [v for v in validations if v.get("independent") is True]
    if not independent or any(v.get("result") != "effective" for v in independent): blockers.append("independent_effectiveness_retest_incomplete")
    if any(d.get("status") not in {"completed", "waived_by_authorized_human"} for d in dependencies): blockers.append("dependencies_unresolved")
    if any(f.get("status") not in {"acknowledged", "closed", "not_required"} for f in follow_ups): blockers.append("regulator_follow_up_unreconciled")
    if entity_checks and any(x.get("implemented") is not True for x in entity_checks): blockers.append("cross_entity_implementation_incomplete")
    score = max(0, 100 - 20 * len(blockers))
    return {"score": score, "ready": not blockers, "blockers": blockers, "human_certification_required": True, "automated_closure_allowed": False, "evidence": ev}


def sustainability_state(observations: list[dict], min_window_days: int = 30) -> dict:
    if not observations: return {"state": "not_started", "reopen_candidate": False, "reasons": ["observations_missing"]}
    days = max((o.get("days_since_closure", 0) for o in observations), default=0)
    failures = [o for o in observations if o.get("control_effective") is False or o.get("recurrence_detected") is True]
    if failures: return {"state": "failed", "reopen_candidate": True, "reasons": ["effectiveness_failure_or_recurrence"]}
    if days < min_window_days: return {"state": "monitoring", "reopen_candidate": False, "reasons": ["minimum_sustainability_window_not_met"]}
    degradation = any(float(o.get("health_score", 100)) < 80 for o in observations)
    return {"state": "degrading" if degradation else "stable", "reopen_candidate": degradation, "reasons": ["health_score_degradation"] if degradation else []}


def recurrence_match(closed_commitment: dict, signals: list[dict]) -> list[dict]:
    out=[]
    keys=(closed_commitment.get("control_id"), closed_commitment.get("obligation_id"), closed_commitment.get("normalized_theme"))
    for s in signals:
        score=0
        if keys[0] and s.get("control_id")==keys[0]: score+=0.45
        if keys[1] and s.get("obligation_id")==keys[1]: score+=0.35
        if keys[2] and s.get("normalized_theme")==keys[2]: score+=0.20
        if score>=0.55: out.append({"signal_id":s.get("signal_id"),"score":round(score,2),"candidate":True})
    return out
