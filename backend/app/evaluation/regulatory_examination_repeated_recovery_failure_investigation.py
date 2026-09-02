from __future__ import annotations
import hashlib, json

def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def reconstruct_recovery_cycles(payload: dict) -> dict:
    cycles=payload.get("cycles", [])
    refs=sorted({str(r) for c in cycles for r in c.get("evidence_refs", []) if r})
    failed=[c for c in cycles if str(c.get("status","")).lower() in {"failed","recurred","decayed","reopened"}]
    missing=[str(c.get("cycle_id")) for c in cycles if not c.get("evidence_refs")]
    return {"cycle_count":len(cycles),"failed_cycle_count":len(failed),"unique_evidence_count":len(refs),"evidence_refs":refs,"cycles_missing_evidence":missing,"evidence_complete":bool(cycles) and not missing,"repeated_failure":len(failed)>=2,"human_validation_required":True}

def validate_recovery_assumptions(payload: dict) -> dict:
    assumptions=payload.get("assumptions", [])
    invalid=[a for a in assumptions if str(a.get("status","unknown")).lower() in {"invalid","failed","unsupported","breached"}]
    unverified=[a for a in assumptions if str(a.get("status","unknown")).lower() not in {"valid","confirmed","invalid","failed","unsupported","breached"}]
    return {"assumption_count":len(assumptions),"invalid_assumption_count":len(invalid),"unverified_assumption_count":len(unverified),"prior_recovery_assumptions_at_risk":bool(invalid or unverified),"human_review_required":bool(invalid or unverified)}

def reassess_recovery_root_causes(payload: dict) -> dict:
    prior=set(payload.get("prior_root_cause_ids", [])); current=set(payload.get("current_root_cause_ids", []))
    shared=sorted(prior & current); new=sorted(current-prior); retired=sorted(prior-current)
    score=min(100,len(shared)*30+len(new)*20+(20 if payload.get("rehabilitation_failed") else 0)+(15 if payload.get("risk_rebound_detected") else 0))
    return {"shared_root_cause_ids":shared,"new_root_cause_ids":new,"retired_root_cause_ids":retired,"persistent_recovery_failure_pattern":bool(shared),"root_cause_reassessment_score":score,"human_confirmation_required":True}

def analyze_failed_rehabilitation(payload: dict) -> dict:
    controls=payload.get("controls", [])
    failed=[c for c in controls if c.get("rehabilitation_effective") is False or c.get("revalidation_passed") is False]
    entities=sorted({str(e) for c in failed for e in c.get("entity_ids", [])})
    return {"control_count":len(controls),"failed_rehabilitation_count":len(failed),"affected_entity_ids":entities,"enterprise_rehabilitation_failure":len(failed)>=2 or len(entities)>=2,"recommendation_only":True,"human_decision_required":bool(failed)}

def map_recovery_causality(payload: dict) -> dict:
    links=payload.get("causal_links", [])
    entities=sorted({str(x) for l in links for x in (l.get("source_entity_id"),l.get("target_entity_id")) if x})
    systemic=[l for l in links if float(l.get("confidence",0))>=0.75 and l.get("shared_root_cause") is True]
    return {"causal_link_count":len(links),"entity_ids":entities,"high_confidence_systemic_link_count":len(systemic),"cross_entity_systemic_recovery_causality":len(systemic)>=1 and len(entities)>=2,"human_validation_required":True}

def regulator_recovery_impact(payload: dict) -> dict:
    items=payload.get("follow_ups", [])
    open_items=[x for x in items if str(x.get("status","open")).lower() not in {"closed","resolved","complete"}]
    same_theme=[x for x in items if x.get("same_recovery_theme") is True or x.get("same_systemic_theme") is True]
    material=any(str(x.get("materiality","low")).lower() in {"high","critical"} for x in items)
    overdue=any(x.get("overdue") is True for x in items)
    return {"follow_up_count":len(items),"open_follow_up_count":len(open_items),"same_theme_count":len(same_theme),"material_regulator_follow_up":material,"overdue_regulator_follow_up":overdue,"renewed_recovery_strategy_impact":bool(open_items or same_theme or material or overdue),"documented_regulator_position_only":True}

def remediation_reauthorization_readiness(payload: dict) -> dict:
    checks={
      "recovery_evidence_reconstructed":bool(payload.get("recovery_evidence_reconstructed")),
      "root_cause_human_confirmed":bool(payload.get("root_cause_human_confirmed")),
      "cross_entity_scope_validated":bool(payload.get("cross_entity_scope_validated")),
      "failed_rehabilitation_assessed":bool(payload.get("failed_rehabilitation_assessed")),
      "independent_internal_audit_challenge_complete":bool(payload.get("independent_internal_audit_challenge_complete")),
      "regulator_follow_up_assessed":bool(payload.get("regulator_follow_up_assessed")),
      "renewed_recovery_strategy_documented":bool(payload.get("renewed_recovery_strategy_documented")),
    }
    blockers=[k for k,v in checks.items() if not v]
    score=round(sum(checks.values())/len(checks)*100,2)
    return {"reauthorization_readiness_score":score,"checks":checks,"blocking_items":blockers,"ready_for_human_authorization":not blockers,"automated_authorization_allowed":False}
