from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def critical_path_status(payload: dict) -> dict:
    milestones = payload.get("milestones", [])
    dependencies = payload.get("dependencies", [])
    blocked = [m for m in milestones if m.get("status") == "blocked"]
    overdue = [m for m in milestones if m.get("overdue") is True]
    critical_dependencies = [d for d in dependencies if d.get("critical") and d.get("status") != "complete"]
    return {
        "blocked_milestones": len(blocked),
        "overdue_milestones": len(overdue),
        "open_critical_dependencies": len(critical_dependencies),
        "critical_path_at_risk": bool(blocked or overdue or critical_dependencies),
    }


def implementation_drift(payload: dict) -> dict:
    expected = payload.get("expected_controls", [])
    actual = payload.get("implemented_controls", [])
    expected_ids = {x.get("control_id") for x in expected}
    actual_ids = {x.get("control_id") for x in actual}
    missing = sorted(x for x in expected_ids - actual_ids if x)
    mismatched = []
    actual_by_id = {x.get("control_id"): x for x in actual}
    for item in expected:
        cid = item.get("control_id")
        if cid in actual_by_id and item.get("design_version") != actual_by_id[cid].get("design_version"):
            mismatched.append(cid)
    total = max(len(expected_ids), 1)
    drift_score = round(min(100.0, 100.0 * (len(missing) + len(mismatched)) / total), 2)
    return {"drift_score": drift_score, "missing_controls": missing, "version_mismatches": sorted(set(mismatched)), "implementation_drift_detected": drift_score > 0}


def effectiveness_kpis(payload: dict) -> dict:
    tests = payload.get("tests", [])
    if not tests:
        return {"pass_rate": 0.0, "evidence_coverage": 0.0, "cross_entity_coverage": 0.0, "kpi_status": "insufficient_evidence"}
    passed = sum(1 for t in tests if t.get("result") == "pass")
    evidenced = sum(1 for t in tests if t.get("evidence_refs"))
    entities = {t.get("entity_id") for t in tests if t.get("entity_id")}
    expected_entities = set(payload.get("expected_entity_ids", []))
    coverage = 100.0 if not expected_entities else 100.0 * len(entities & expected_entities) / len(expected_entities)
    return {
        "pass_rate": round(100.0 * passed / len(tests), 2),
        "evidence_coverage": round(100.0 * evidenced / len(tests), 2),
        "cross_entity_coverage": round(coverage, 2),
        "kpi_status": "on_track" if passed == len(tests) and coverage >= 100 else "attention_required",
    }


def recovery_assurance_readiness(payload: dict) -> dict:
    blockers = []
    if not payload.get("all_required_milestones_complete"): blockers.append("milestones_incomplete")
    if not payload.get("implementation_evidence_complete"): blockers.append("implementation_evidence_incomplete")
    if not payload.get("independent_recovery_testing_passed"): blockers.append("independent_recovery_testing_not_passed")
    if not payload.get("cross_entity_validation_complete"): blockers.append("cross_entity_validation_incomplete")
    if payload.get("critical_path_at_risk"): blockers.append("critical_path_at_risk")
    if payload.get("implementation_drift_detected"): blockers.append("implementation_drift_detected")
    return {"ready_for_human_residual_risk_reassessment": not blockers, "blockers": blockers}


def residual_systemic_risk(payload: dict) -> dict:
    baseline = float(payload.get("baseline_risk_score", 0))
    current = float(payload.get("current_risk_score", baseline))
    reduction = max(0.0, baseline-current)
    pct = 0.0 if baseline <= 0 else round(100.0 * reduction / baseline, 2)
    return {"baseline_risk_score": baseline, "current_risk_score": current, "risk_reduction": round(reduction,2), "risk_reduction_percent": pct, "human_acceptance_required": True}
