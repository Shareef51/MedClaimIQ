from __future__ import annotations
import hashlib,json
def version_hash(payload:dict)->str: return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()
def reconstruct_systemic_decay(payload:dict)->dict:
 cycles=payload.get("decay_cycles",[]); refs=sorted({str(r) for c in cycles for r in c.get("evidence_refs",[]) if r}); missing=[str(c.get("cycle_id")) for c in cycles if not c.get("evidence_refs")]
 root_patterns={str(c.get("root_cause_id")) for c in cycles if c.get("root_cause_id")}; entities={str(e) for c in cycles for e in c.get("entity_ids",[]) if e}
 return {"cycle_count":len(cycles),"unique_evidence_count":len(refs),"evidence_refs":refs,"cycles_missing_evidence":missing,"distinct_root_cause_count":len(root_patterns),"affected_entity_count":len(entities),"systemic_decay_reconstructed":bool(cycles) and not missing,"human_validation_required":True}
def validate_prior_recovery_assumptions(payload:dict)->dict:
 assumptions=payload.get("assumptions",[]); invalid=[a for a in assumptions if str(a.get("status","unknown")).lower() in {"invalid","failed","unsupported","breached"}]; unverified=[a for a in assumptions if str(a.get("status","unknown")).lower() not in {"valid","confirmed","invalid","failed","unsupported","breached"}]
 return {"assumption_count":len(assumptions),"invalid_assumption_count":len(invalid),"unverified_assumption_count":len(unverified),"prior_recovery_assumptions_at_risk":bool(invalid or unverified),"human_review_required":bool(invalid or unverified)}
def reassess_decay_root_causes(payload:dict)->dict:
 prior=set(payload.get("prior_root_cause_ids",[])); current=set(payload.get("current_root_cause_ids",[])); shared=sorted(prior&current); new=sorted(current-prior)
 score=min(100,len(shared)*35+len(new)*20+(25 if payload.get("recovery_control_failed") else 0))
 return {"shared_root_cause_ids":shared,"new_root_cause_ids":new,"persistent_root_cause_pattern":bool(shared),"decay_root_cause_score":score,"human_confirmation_required":True}
def analyze_cross_entity_control_gaps(payload:dict)->dict:
 gaps=payload.get("control_gaps",[]); material=[g for g in gaps if str(g.get("severity","low")).lower() in {"high","critical"} or g.get("recovery_control_failed") is True]; entities=sorted({str(e) for g in material for e in g.get("entity_ids",[]) if e})
 return {"control_gap_count":len(gaps),"material_gap_count":len(material),"affected_entity_ids":entities,"enterprise_control_gap":len(material)>=2 or len(entities)>=2,"recommendation_only":True,"human_decision_required":bool(material)}
def regulator_follow_up_impact(payload:dict)->dict:
 items=payload.get("follow_ups",[]); open_items=[x for x in items if str(x.get("status","open")).lower() not in {"closed","resolved","complete"}]; same=[x for x in items if x.get("same_recovery_theme") is True]
 return {"follow_up_count":len(items),"open_follow_up_count":len(open_items),"same_recovery_theme_count":len(same),"renewed_remediation_impact":bool(open_items or same),"documented_regulator_position_only":True}
def commitment_alignment(payload:dict)->dict:
 cs=payload.get("commitments",[]); blocked=[c for c in cs if str(c.get("status","open")).lower() in {"overdue","blocked","breached"}]; unlinked=[c for c in cs if not c.get("remediation_workstream_id")]
 return {"commitment_count":len(cs),"blocked_commitment_count":len(blocked),"unlinked_commitment_count":len(unlinked),"alignment_complete":bool(cs) and not blocked and not unlinked,"human_reconciliation_required":True}
def authorization_readiness(payload:dict)->dict:
 checks={"systemic_decay_reconstructed":bool(payload.get("systemic_decay_reconstructed")),"root_cause_human_confirmed":bool(payload.get("root_cause_human_confirmed")),"cross_entity_gap_scope_validated":bool(payload.get("cross_entity_gap_scope_validated")),"regulator_follow_up_assessed":bool(payload.get("regulator_follow_up_assessed")),"commitment_alignment_complete":bool(payload.get("commitment_alignment_complete")),"independent_challenge_complete":bool(payload.get("independent_challenge_complete")),"renewed_strategy_documented":bool(payload.get("renewed_strategy_documented"))}
 score=round(sum(checks.values())/len(checks)*100,2); blockers=[k for k,v in checks.items() if not v]
 return {"authorization_readiness_score":score,"checks":checks,"blocking_items":blockers,"ready_for_human_authorization":not blockers,"automated_authorization_allowed":False}
