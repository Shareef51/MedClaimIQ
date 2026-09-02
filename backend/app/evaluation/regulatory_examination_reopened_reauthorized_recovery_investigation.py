from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def reconstruct_reopened_recovery_cycles(payload: dict) -> dict:
    cycles = payload.get("cycles", [])
    ordered = sorted(cycles, key=lambda x: (int(x.get("sequence", 0) or 0), str(x.get("cycle_id", ""))))
    failed_states = {"failed", "recurred", "decayed", "reopened", "regressed", "breached"}
    failed = [c for c in ordered if str(c.get("status", "")).lower() in failed_states]
    refs = sorted({str(r) for c in ordered for r in c.get("evidence_refs", []) if r})
    missing = [str(c.get("cycle_id")) for c in ordered if not c.get("evidence_refs")]
    human_reclosures = [c for c in ordered if bool(c.get("human_reclosure")) or c.get("reclosure_version_id")]
    human_reopenings = [c for c in ordered if bool(c.get("human_reopening")) or c.get("reopening_version_id")]
    return {
        "cycle_count": len(ordered),
        "failed_or_recurred_cycle_count": len(failed),
        "human_reclosure_count": len(human_reclosures),
        "human_reopening_count": len(human_reopenings),
        "unique_evidence_count": len(refs),
        "evidence_refs": refs,
        "cycles_missing_evidence": missing,
        "multi_cycle_evidence_complete": bool(ordered) and not missing,
        "repeated_failure_pattern": len(failed) >= 2,
        "human_validation_required": True,
    }


def reconstruct_repeated_failure_root_causes(payload: dict) -> dict:
    prior = set(map(str, payload.get("prior_root_cause_ids", [])))
    current = set(map(str, payload.get("current_root_cause_ids", [])))
    historical = set(map(str, payload.get("historical_root_cause_ids", [])))
    persistent = sorted((prior & current) | (historical & current))
    newly_emergent = sorted(current - prior - historical)
    unresolved_historical = sorted(historical & current)
    retired = sorted((prior | historical) - current)
    repeated_control_failures = int(payload.get("repeated_control_failure_count", 0) or 0)
    rebound = bool(payload.get("systemic_risk_rebound_confirmed"))
    propagation = bool(payload.get("cross_entity_recurrence_confirmed"))
    score = min(
        100,
        len(persistent) * 22
        + len(newly_emergent) * 12
        + min(repeated_control_failures, 5) * 9
        + (14 if rebound else 0)
        + (12 if propagation else 0),
    )
    return {
        "persistent_root_cause_ids": persistent,
        "newly_emergent_root_cause_ids": newly_emergent,
        "unresolved_historical_root_cause_ids": unresolved_historical,
        "retired_root_cause_ids": retired,
        "repeated_failure_root_cause_score": score,
        "persistent_systemic_cause_candidate": bool(persistent) and (repeated_control_failures > 0 or rebound or propagation),
        "human_root_cause_confirmation_required": True,
        "automated_root_cause_conclusion_allowed": False,
    }


def reassess_prior_recertification_assumptions(payload: dict) -> dict:
    assumptions = payload.get("assumptions", [])
    breached_states = {"breached", "invalid", "failed", "unsupported", "expired", "stale"}
    confirmed_states = {"valid", "confirmed", "sustained"}
    breached = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() in breached_states]
    unverified = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() not in breached_states | confirmed_states]
    materially_changed = [a for a in assumptions if bool(a.get("material_change"))]
    return {
        "assumption_count": len(assumptions),
        "breached_assumption_ids": sorted(str(a.get("assumption_id")) for a in breached if a.get("assumption_id")),
        "unverified_assumption_ids": sorted(str(a.get("assumption_id")) for a in unverified if a.get("assumption_id")),
        "materially_changed_assumption_ids": sorted(str(a.get("assumption_id")) for a in materially_changed if a.get("assumption_id")),
        "prior_recertification_assumptions_at_risk": bool(breached or unverified or materially_changed),
        "human_reassessment_required": bool(breached or unverified or materially_changed),
    }


def analyze_re_rehabilitation_failures(payload: dict) -> dict:
    controls = payload.get("controls", [])
    failed = []
    for control in controls:
        status = str(control.get("status", "")).lower()
        if (
            control.get("re_rehabilitation_effective") is False
            or control.get("independent_revalidation_passed") is False
            or status in {"failed", "regressed", "ineffective", "recurred", "breached"}
        ):
            failed.append(control)
    affected_entities = sorted({str(e) for c in failed for e in c.get("entity_ids", []) if e})
    repeated_controls = sorted(str(c.get("control_id")) for c in failed if int(c.get("failure_cycle_count", 0) or 0) >= 2 and c.get("control_id"))
    return {
        "control_count": len(controls),
        "failed_re_rehabilitation_count": len(failed),
        "repeated_failure_control_ids": repeated_controls,
        "affected_entity_ids": affected_entities,
        "enterprise_re_rehabilitation_failure": len(failed) >= 2 or len(affected_entities) >= 2 or bool(repeated_controls),
        "recommendation_only": True,
        "human_control_redesign_decision_required": bool(failed),
    }


def map_reopened_cross_entity_causality(payload: dict) -> dict:
    links = payload.get("causal_links", [])
    validated = [x for x in links if bool(x.get("human_validated"))]
    high_confidence = [x for x in links if float(x.get("confidence", 0) or 0) >= 0.75]
    systemic = [x for x in high_confidence if bool(x.get("shared_root_cause")) or bool(x.get("shared_control_failure"))]
    entities = sorted({str(v) for x in links for v in (x.get("source_entity_id"), x.get("target_entity_id")) if v})
    unvalidated = [str(x.get("link_id")) for x in high_confidence if not x.get("human_validated") and x.get("link_id")]
    return {
        "causal_link_count": len(links),
        "human_validated_link_count": len(validated),
        "high_confidence_systemic_link_count": len(systemic),
        "entity_ids": entities,
        "unvalidated_high_confidence_link_ids": sorted(unvalidated),
        "cross_entity_systemic_causality_candidate": len(systemic) >= 1 and len(entities) >= 2,
        "human_validation_required": bool(unvalidated) or bool(systemic),
    }


def regulator_followup_impact(payload: dict) -> dict:
    items = payload.get("followups", [])
    linked = [x for x in items if bool(x.get("linked_to_reopened_recovery")) or bool(x.get("linked_to_repeated_failure"))]
    open_items = [x for x in linked if str(x.get("status", "open")).lower() not in {"closed", "resolved", "complete"}]
    overdue = [x for x in linked if bool(x.get("overdue"))]
    material = [x for x in linked if str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    return {
        "followup_count": len(items),
        "linked_followup_count": len(linked),
        "open_linked_followup_count": len(open_items),
        "overdue_linked_followup_count": len(overdue),
        "material_linked_followup_count": len(material),
        "renewed_recovery_strategy_impact_candidate": bool(open_items or overdue or material),
        "regulator_intent_inferred": False,
        "human_interpretation_required": bool(linked),
    }


def recovery_reauthorization_readiness(payload: dict) -> dict:
    checks = {
        "release90_human_reopening_verified": bool(payload.get("release90_human_reopening_verified")),
        "multi_cycle_evidence_reconstructed": bool(payload.get("multi_cycle_evidence_reconstructed")),
        "prior_recertification_assumptions_reassessed": bool(payload.get("prior_recertification_assumptions_reassessed")),
        "repeated_failure_root_cause_human_confirmed": bool(payload.get("repeated_failure_root_cause_human_confirmed")),
        "cross_entity_causality_human_validated": bool(payload.get("cross_entity_causality_human_validated")),
        "failed_re_rehabilitation_assessed": bool(payload.get("failed_re_rehabilitation_assessed")),
        "regulator_followups_human_interpreted": bool(payload.get("regulator_followups_human_interpreted")),
        "renewed_recovery_strategy_documented": bool(payload.get("renewed_recovery_strategy_documented")),
        "independent_internal_audit_challenge_complete": bool(payload.get("independent_internal_audit_challenge_complete")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
    }
    blockers = [k for k, v in checks.items() if not v]
    score = round(100.0 * sum(checks.values()) / len(checks), 2)
    return {
        "recovery_reauthorization_readiness_score": score,
        "checks": checks,
        "blocking_items": blockers,
        "ready_for_human_supervisory_reauthorization": not blockers,
        "automated_reauthorization_allowed": False,
    }
