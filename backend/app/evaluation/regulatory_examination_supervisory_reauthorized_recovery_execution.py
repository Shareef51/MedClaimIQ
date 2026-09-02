from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def supervisory_program_progress(payload: dict) -> dict:
    workstreams = payload.get("workstreams", [])
    total = len(workstreams)
    completed = sum(1 for x in workstreams if str(x.get("status", "")).lower() in {"complete", "completed", "done"})
    blocked = [x for x in workstreams if str(x.get("status", "")).lower() in {"blocked", "overdue", "failed"}]
    repeated = [x for x in workstreams if bool(x.get("repeated_failure_scope")) or int(x.get("prior_failure_count", 0) or 0) >= 2]
    approved = [x for x in workstreams if x.get("human_approval_reference")]
    progress = round(completed / total * 100, 2) if total else 0.0
    return {
        "workstream_count": total,
        "completed_workstream_count": completed,
        "blocked_workstream_count": len(blocked),
        "repeated_failure_workstream_count": len(repeated),
        "human_approved_workstream_count": len(approved),
        "progress_percent": progress,
        "executive_attention_required": bool(blocked),
    }


def control_retransformation_status(payload: dict) -> dict:
    controls = payload.get("controls", [])
    repeated = [c for c in controls if bool(c.get("repeated_failure")) or int(c.get("failure_count", 0) or 0) >= 2]
    transformed = [c for c in controls if str(c.get("action", "")).lower() in {"replace", "replacement", "redesign", "retransform", "re-transform", "re-transformation"}]
    evidence_bound = [c for c in transformed if c.get("implementation_evidence_refs")]
    unapproved = [c for c in transformed if not c.get("human_approval_reference")]
    missing_release91_scope = [c for c in transformed if not c.get("release91_reauthorization_scope_reference")]
    entities = sorted({str(e) for c in controls for e in c.get("entity_ids", []) if e})
    return {
        "control_count": len(controls),
        "repeated_failure_control_count": len(repeated),
        "replacement_or_retransformation_count": len(transformed),
        "evidence_bound_control_count": len(evidence_bound),
        "missing_human_approval_count": len(unapproved),
        "missing_release91_scope_reference_count": len(missing_release91_scope),
        "affected_entity_ids": entities,
        "human_approval_required": bool(transformed),
        "automated_control_approval_allowed": False,
    }


def deployment_sequence_assessment(payload: dict) -> dict:
    steps = payload.get("deployment_steps", [])
    sequence_values = [int(x.get("sequence", 0) or 0) for x in steps if x.get("sequence") is not None]
    duplicates = sorted({x for x in sequence_values if sequence_values.count(x) > 1})
    blocked = [x for x in steps if str(x.get("status", "")).lower() in {"blocked", "failed", "overdue"}]
    dependency_gaps = [x for x in steps if x.get("dependency_ids") and not x.get("dependencies_satisfied", False)]
    unapproved = [x for x in steps if not x.get("human_sequence_approval_reference")]
    entities = sorted({str(e) for x in steps for e in x.get("entity_ids", []) if e})
    return {
        "deployment_step_count": len(steps),
        "duplicate_sequence_numbers": duplicates,
        "blocked_step_count": len(blocked),
        "unsatisfied_dependency_count": len(dependency_gaps),
        "missing_human_sequence_approval_count": len(unapproved),
        "entity_ids": entities,
        "sequence_at_risk": bool(duplicates or blocked or dependency_gaps or unapproved),
    }


def critical_path_assessment(payload: dict) -> dict:
    milestones = payload.get("milestones", [])
    critical = [m for m in milestones if m.get("critical_path") is True]
    blocked = [m for m in critical if str(m.get("status", "")).lower() in {"blocked", "overdue", "failed"}]
    stale = [m for m in critical if not m.get("evidence_refs") or m.get("evidence_fresh") is False]
    dependency_gaps = [m for m in critical if m.get("dependency_ids") and not m.get("dependencies_satisfied", False)]
    return {
        "milestone_count": len(milestones),
        "critical_path_count": len(critical),
        "blocked_critical_count": len(blocked),
        "stale_or_missing_evidence_count": len(stale),
        "critical_dependency_gap_count": len(dependency_gaps),
        "critical_path_at_risk": bool(blocked or stale or dependency_gaps),
    }


def implementation_drift(payload: dict) -> dict:
    planned = payload.get("planned_controls", [])
    actual = payload.get("implemented_controls", [])
    p = {str(x.get("control_id")): x for x in planned if x.get("control_id")}
    a = {str(x.get("control_id")): x for x in actual if x.get("control_id")}
    missing = sorted(set(p) - set(a))
    changed = sorted(k for k in set(p) & set(a) if str(p[k].get("design_fingerprint", "")) != str(a[k].get("design_fingerprint", "")))
    unauthorized = sorted(k for k, v in a.items() if not v.get("human_approval_reference"))
    out_of_scope = sorted(k for k, v in a.items() if not v.get("release91_reauthorization_scope_reference"))
    score = min(100, len(missing) * 25 + len(changed) * 25 + len(unauthorized) * 30 + len(out_of_scope) * 20)
    return {
        "missing_control_ids": missing,
        "design_drift_control_ids": changed,
        "missing_human_approval_control_ids": unauthorized,
        "missing_release91_scope_control_ids": out_of_scope,
        "implementation_drift_score": score,
        "material_drift": score >= 50,
        "human_review_required": bool(missing or changed or unauthorized or out_of_scope),
    }


def recovery_kpi_assessment(payload: dict) -> dict:
    metrics = payload.get("metrics", [])
    breached = []
    improved = 0
    independently_sourced = 0
    for m in metrics:
        actual = m.get("actual")
        target = m.get("target")
        baseline = m.get("baseline")
        direction = str(m.get("direction", "higher_is_better")).lower()
        if m.get("evidence_ref"):
            independently_sourced += 1
        if actual is not None and baseline is not None:
            if (direction == "lower_is_better" and float(actual) < float(baseline)) or (direction != "lower_is_better" and float(actual) > float(baseline)):
                improved += 1
        if actual is not None and target is not None:
            failed = (direction == "lower_is_better" and float(actual) > float(target)) or (direction != "lower_is_better" and float(actual) < float(target))
            if failed:
                breached.append(m)
    score = round((len(metrics) - len(breached)) / len(metrics) * 100, 2) if metrics else 0.0
    return {
        "metric_count": len(metrics),
        "breached_metric_count": len(breached),
        "improved_vs_baseline_count": improved,
        "evidence_bound_metric_count": independently_sourced,
        "recovery_kpi_score": score,
        "recovery_target_met": bool(metrics) and not breached,
        "human_interpretation_required": True,
    }


def independent_recovery_assurance(payload: dict) -> dict:
    tests = payload.get("tests", [])
    failed = [t for t in tests if str(t.get("result", "")).lower() in {"fail", "failed", "ineffective"}]
    independent = all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
    release91_scope = all(t.get("release91_reauthorization_scope_validated") is True for t in tests) if tests else False
    cross_entity = all(t.get("cross_entity_effectiveness_validated") is True for t in tests) if tests else False
    repeated_failure = all(t.get("repeated_failure_scope_validated") is True for t in tests) if tests else False
    entities = sorted({str(e) for t in tests for e in t.get("entity_ids", []) if e})
    return {
        "test_count": len(tests),
        "failed_test_count": len(failed),
        "validated_entity_ids": entities,
        "independence_complete": independent,
        "release91_reauthorization_scope_validated": release91_scope,
        "cross_entity_effectiveness_validated": cross_entity,
        "repeated_failure_scope_validated": repeated_failure,
        "assurance_passed": bool(tests) and not failed and independent and release91_scope and cross_entity and repeated_failure,
        "human_certification_required": True,
        "automated_certification_allowed": False,
    }


def execution_readiness(payload: dict) -> dict:
    checks = {
        "release91_supervisory_reauthorization_reference_present": bool(payload.get("release91_supervisory_reauthorization_reference_present")),
        "supervisory_workstreams_defined": bool(payload.get("supervisory_workstreams_defined")),
        "control_retransformation_scope_human_approved": bool(payload.get("control_retransformation_scope_human_approved")),
        "cross_entity_sequence_validated": bool(payload.get("cross_entity_sequence_validated")),
        "regulatory_commitment_alignment_complete": bool(payload.get("regulatory_commitment_alignment_complete")),
        "critical_path_reviewed": bool(payload.get("critical_path_reviewed")),
        "execution_evidence_current": bool(payload.get("execution_evidence_current")),
        "recovery_kpis_baselined": bool(payload.get("recovery_kpis_baselined")),
        "independent_recovery_assurance_complete": bool(payload.get("independent_recovery_assurance_complete")),
    }
    blockers = [k for k, v in checks.items() if not v]
    score = round(sum(checks.values()) / len(checks) * 100, 2)
    return {
        "execution_readiness_score": score,
        "checks": checks,
        "blocking_items": blockers,
        "ready_for_human_outcome_review": not blockers,
        "automated_certification_allowed": False,
        "automated_risk_acceptance_allowed": False,
        "automated_commitment_closure_allowed": False,
        "automated_program_reclosure_allowed": False,
    }
