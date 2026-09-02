from __future__ import annotations
import hashlib
import json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def reconstruct_multi_cycle_supervisory_evidence(payload: dict) -> dict:
    cycles = payload.get("cycles", [])
    ordered = sorted(cycles, key=lambda x: (int(x.get("sequence", 0) or 0), str(x.get("cycle_id", ""))))
    adverse = {"failed", "recurred", "decayed", "reopened", "regressed", "breached", "ineffective"}
    failed = [c for c in ordered if str(c.get("status", "")).lower() in adverse]
    evidence = sorted({str(r) for c in ordered for r in c.get("evidence_refs", []) if r})
    missing = [str(c.get("cycle_id")) for c in ordered if not c.get("evidence_refs") and c.get("cycle_id")]
    reclosures = [c for c in ordered if bool(c.get("human_reclosure")) or c.get("reclosure_version_id")]
    reopenings = [c for c in ordered if bool(c.get("human_reopening")) or c.get("reopening_version_id")]
    assurance = [c for c in ordered if c.get("independent_assurance_version_id") or bool(c.get("independent_assurance_complete"))]
    return {
        "cycle_count": len(ordered),
        "failed_or_recurred_cycle_count": len(failed),
        "human_reclosure_count": len(reclosures),
        "human_reopening_count": len(reopenings),
        "independent_assurance_cycle_count": len(assurance),
        "evidence_refs": evidence,
        "unique_evidence_count": len(evidence),
        "cycles_missing_evidence": missing,
        "full_multi_cycle_evidence_reconstructed": bool(ordered) and not missing,
        "repeated_supervisory_failure_pattern": len(failed) >= 2,
        "human_evidence_validation_required": True,
    }


def reconstruct_persistent_emergent_root_causes(payload: dict) -> dict:
    prior = set(map(str, payload.get("prior_root_cause_ids", [])))
    historical = set(map(str, payload.get("historical_root_cause_ids", [])))
    current = set(map(str, payload.get("current_root_cause_ids", [])))
    persistent = sorted(current & (prior | historical))
    emergent = sorted(current - prior - historical)
    unresolved_historical = sorted(current & historical)
    retired = sorted((prior | historical) - current)
    repeated_control_failures = int(payload.get("repeated_control_retransformation_failure_count", payload.get("repeated_control_failure_count", 0)) or 0)
    rebound = bool(payload.get("systemic_risk_rebound_confirmed"))
    propagation = bool(payload.get("cross_entity_recurrence_confirmed"))
    regulator_pressure = bool(payload.get("material_regulator_followup_confirmed"))
    score = min(100.0, round(
        len(persistent)*20 + len(emergent)*10 + min(repeated_control_failures, 6)*8 +
        (14 if rebound else 0) + (12 if propagation else 0) + (8 if regulator_pressure else 0), 2
    ))
    return {
        "persistent_root_cause_ids": persistent,
        "emergent_root_cause_ids": emergent,
        "unresolved_historical_root_cause_ids": unresolved_historical,
        "retired_root_cause_ids": retired,
        "multi_cycle_root_cause_risk_score": score,
        "persistent_systemic_root_cause_candidate": bool(persistent) and (repeated_control_failures > 0 or rebound or propagation),
        "emergent_systemic_root_cause_candidate": bool(emergent) and (rebound or propagation or regulator_pressure),
        "human_root_cause_confirmation_required": True,
        "automated_root_cause_conclusion_allowed": False,
    }


def validate_prior_recertification_reclosure_assumptions(payload: dict) -> dict:
    assumptions = payload.get("assumptions", [])
    bad = {"breached", "invalid", "failed", "unsupported", "expired", "stale", "contradicted"}
    good = {"valid", "confirmed", "sustained", "supported"}
    breached = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() in bad]
    unverified = [a for a in assumptions if str(a.get("current_status", a.get("status", "unknown"))).lower() not in bad | good]
    material = [a for a in assumptions if bool(a.get("material_change")) or bool(a.get("new_evidence_contradicts"))]
    return {
        "assumption_count": len(assumptions),
        "breached_assumption_ids": sorted(str(a.get("assumption_id")) for a in breached if a.get("assumption_id")),
        "unverified_assumption_ids": sorted(str(a.get("assumption_id")) for a in unverified if a.get("assumption_id")),
        "materially_changed_assumption_ids": sorted(str(a.get("assumption_id")) for a in material if a.get("assumption_id")),
        "prior_executive_recertification_reclosure_assumptions_at_risk": bool(breached or unverified or material),
        "human_assumption_validation_required": bool(breached or unverified or material),
    }


def analyze_repeated_control_retransformation_failures(payload: dict) -> dict:
    controls = payload.get("controls", [])
    failed = []
    for c in controls:
        status = str(c.get("status", "")).lower()
        if c.get("retransformation_effective") is False or c.get("independent_revalidation_passed") is False or status in {"failed", "regressed", "ineffective", "recurred", "breached"}:
            failed.append(c)
    repeated = sorted(str(c.get("control_id")) for c in failed if c.get("control_id") and int(c.get("failure_cycle_count", 0) or 0) >= 2)
    entities = sorted({str(e) for c in failed for e in c.get("entity_ids", []) if e})
    root_causes = sorted({str(r) for c in failed for r in c.get("root_cause_ids", []) if r})
    return {
        "control_count": len(controls),
        "failed_control_retransformation_count": len(failed),
        "repeated_failure_control_ids": repeated,
        "affected_entity_ids": entities,
        "linked_root_cause_ids": root_causes,
        "enterprise_retransformation_failure_candidate": bool(repeated) or len(failed) >= 2 or len(entities) >= 2,
        "human_control_transformation_decision_required": bool(failed),
        "recommendation_only": True,
    }


def map_cross_entity_causal_propagation(payload: dict) -> dict:
    links = payload.get("causal_links", [])
    high = [x for x in links if float(x.get("confidence", 0) or 0) >= 0.75]
    validated = [x for x in high if bool(x.get("human_validated"))]
    systemic = [x for x in high if bool(x.get("shared_root_cause")) or bool(x.get("shared_control_failure")) or bool(x.get("propagation_evidence"))]
    entities = sorted({str(v) for x in links for v in (x.get("source_entity_id"), x.get("target_entity_id")) if v})
    unvalidated = sorted(str(x.get("link_id")) for x in high if not x.get("human_validated") and x.get("link_id"))
    return {
        "causal_link_count": len(links),
        "high_confidence_link_count": len(high),
        "human_validated_high_confidence_link_count": len(validated),
        "systemic_propagation_link_count": len(systemic),
        "entity_ids": entities,
        "unvalidated_high_confidence_link_ids": unvalidated,
        "cross_entity_systemic_propagation_candidate": len(systemic) >= 1 and len(entities) >= 2,
        "human_validation_required": bool(unvalidated or systemic),
    }


def assess_regulator_followup_impact(payload: dict) -> dict:
    followups = payload.get("followups", [])
    linked = [x for x in followups if bool(x.get("linked_to_reopened_supervisory_recovery")) or bool(x.get("linked_to_repeated_failure"))]
    open_items = [x for x in linked if str(x.get("status", "open")).lower() not in {"closed", "resolved", "complete"}]
    overdue = [x for x in linked if bool(x.get("overdue"))]
    material = [x for x in linked if str(x.get("materiality", "low")).lower() in {"high", "critical"}]
    commitments = sorted({str(x.get("commitment_id")) for x in linked if x.get("commitment_id")})
    return {
        "followup_count": len(followups),
        "linked_followup_count": len(linked),
        "open_linked_followup_count": len(open_items),
        "overdue_linked_followup_count": len(overdue),
        "material_linked_followup_count": len(material),
        "linked_commitment_ids": commitments,
        "material_regulator_followup_impact_candidate": bool(material or overdue),
        "human_regulator_interpretation_required": bool(linked),
        "regulator_intent_inference_allowed": False,
    }


def classify_enterprise_systemic_failure(payload: dict) -> dict:
    root_score = float(payload.get("multi_cycle_root_cause_risk_score", 0) or 0)
    failed_controls = int(payload.get("failed_control_retransformation_count", 0) or 0)
    affected_entities = int(payload.get("affected_entity_count", 0) or 0)
    rebound = float(payload.get("systemic_risk_rebound_percent", 0) or 0)
    repeat_cycles = int(payload.get("repeated_failure_cycle_count", 0) or 0)
    material_followups = int(payload.get("material_regulator_followup_count", 0) or 0)
    score = min(100.0, round(
        root_score*0.35 + min(failed_controls, 5)*8 + min(affected_entities, 6)*5 + min(rebound, 100)*0.15 + min(repeat_cycles, 5)*5 + min(material_followups, 3)*5,
        2,
    ))
    classification = "enterprise_critical" if score >= 75 else "enterprise_systemic" if score >= 55 else "material" if score >= 35 else "localized"
    return {
        "enterprise_systemic_failure_score": score,
        "proposed_enterprise_systemic_failure_classification": classification,
        "enterprise_systemic_failure_candidate": classification in {"enterprise_systemic", "enterprise_critical"},
        "executive_internal_audit_challenge_required": classification in {"enterprise_systemic", "enterprise_critical"},
        "human_classification_confirmation_required": True,
        "automated_authoritative_classification_allowed": False,
    }


def enterprise_recovery_reauthorization_readiness(payload: dict) -> dict:
    gates = {
        "release94_human_reopening_verified": bool(payload.get("release94_human_reopening_verified")),
        "formal_investigation_complete": bool(payload.get("formal_investigation_complete")),
        "full_multi_cycle_evidence_reconstructed": bool(payload.get("full_multi_cycle_evidence_reconstructed")),
        "prior_recertification_reclosure_assumptions_validated": bool(payload.get("prior_recertification_reclosure_assumptions_validated")),
        "persistent_emergent_root_causes_human_confirmed": bool(payload.get("persistent_emergent_root_causes_human_confirmed")),
        "repeated_control_retransformation_failure_assessed": bool(payload.get("repeated_control_retransformation_failure_assessed")),
        "cross_entity_causal_propagation_human_validated": bool(payload.get("cross_entity_causal_propagation_human_validated")),
        "regulator_followup_impact_human_interpreted": bool(payload.get("regulator_followup_impact_human_interpreted")),
        "enterprise_systemic_failure_classification_human_confirmed": bool(payload.get("enterprise_systemic_failure_classification_human_confirmed")),
        "renewed_recovery_strategy_documented": bool(payload.get("renewed_recovery_strategy_documented")),
        "independent_internal_audit_challenge_complete": bool(payload.get("independent_internal_audit_challenge_complete")),
        "executive_review_complete": bool(payload.get("executive_review_complete")),
        "evidence_bound_reauthorization_package_complete": bool(payload.get("evidence_bound_reauthorization_package_complete")),
    }
    blockers = [k for k, v in gates.items() if not v]
    score = round(100.0 * (len(gates)-len(blockers)) / len(gates), 2)
    return {
        "gates": gates,
        "blockers": blockers,
        "enterprise_recovery_reauthorization_readiness_score": score,
        "ready_for_human_enterprise_recovery_reauthorization": not blockers,
        "automated_reauthorization_allowed": False,
    }


def supervisory_dashboard_summary(payload: dict) -> dict:
    return {
        "recovery_program_id": payload.get("recovery_program_id"),
        "investigation_status": payload.get("investigation_status", "open"),
        "multi_cycle_root_cause_risk_score": float(payload.get("multi_cycle_root_cause_risk_score", 0) or 0),
        "enterprise_systemic_failure_score": float(payload.get("enterprise_systemic_failure_score", 0) or 0),
        "affected_entity_count": int(payload.get("affected_entity_count", 0) or 0),
        "repeated_failure_control_count": int(payload.get("repeated_failure_control_count", 0) or 0),
        "open_regulator_followup_count": int(payload.get("open_regulator_followup_count", 0) or 0),
        "human_reauthorization_pending": bool(payload.get("human_reauthorization_pending", True)),
        "monitoring_only": True,
    }


def audit_export_manifest(payload: dict) -> dict:
    refs = sorted({str(x) for x in payload.get("version_refs", []) if x})
    evidence = sorted({str(x) for x in payload.get("evidence_refs", []) if x})
    canonical = {"version_refs": refs, "evidence_refs": evidence, "recovery_program_id": payload.get("recovery_program_id")}
    return {
        **canonical,
        "version_ref_count": len(refs),
        "evidence_ref_count": len(evidence),
        "manifest_hash": version_hash(canonical),
        "human_authority_records_required": True,
    }
