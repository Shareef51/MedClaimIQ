from __future__ import annotations
import hashlib, json

def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def remediation_program_progress(payload: dict) -> dict:
    ws=payload.get("workstreams",[]); total=len(ws)
    done=[x for x in ws if str(x.get("status","")).lower() in {"complete","completed","done"}]
    blocked=[x for x in ws if str(x.get("status","")).lower() in {"blocked","failed","overdue"}]
    bound=[x for x in ws if x.get("release103_reauthorization_scope_reference") and x.get("evidence_refs")]
    systemic=[x for x in ws if x.get("systemic_scope") or len(x.get("entity_ids",[]))>=2]
    return {"workstream_count":total,"completed_workstream_count":len(done),"blocked_workstream_count":len(blocked),"systemic_workstream_count":len(systemic),"release103_evidence_bound_workstream_count":len(bound),"progress_percent":round(len(done)/total*100,2) if total else 0.0,"executive_attention_required":bool(blocked)}

def root_cause_treatment_mapping(payload: dict) -> dict:
    items=payload.get("root_cause_treatments",[])
    persistent=[x for x in items if str(x.get("root_cause_class","")).lower()=="persistent"]
    emergent=[x for x in items if str(x.get("root_cause_class","")).lower()=="emergent"]
    missing=[x for x in items if not x.get("root_cause_id") or not x.get("remediation_workstream_id") or not x.get("control_ids") or not x.get("evidence_refs") or not x.get("release103_reauthorization_scope_reference") or not x.get("human_treatment_owner_confirmation_reference")]
    entities=sorted({str(e) for x in items for e in x.get("entity_ids",[]) if e})
    return {"treatment_count":len(items),"persistent_treatment_count":len(persistent),"emergent_treatment_count":len(emergent),"mapped_entity_ids":entities,"incomplete_treatment_mapping_count":len(missing),"treatment_mapping_complete":bool(items) and not missing,"human_root_cause_treatment_confirmation_required":True}

def systemic_control_retransformation_status(payload: dict) -> dict:
    controls=payload.get("controls",[]); actions={"replace","replacement","redesign","retransform","re-transform","re-transformation","retire-and-replace"}
    transformed=[c for c in controls if str(c.get("action","")).lower() in actions]
    repeated=[c for c in controls if c.get("repeated_failure") or int(c.get("failure_cycle_count",c.get("failure_count",0)) or 0)>=2]
    approved=[c for c in transformed if c.get("human_control_retransformation_approval_reference")]
    evidence=[c for c in transformed if c.get("implementation_evidence_refs")]
    scope_missing=[c for c in transformed if not c.get("release103_reauthorization_scope_reference")]
    root_missing=[c for c in transformed if not c.get("root_cause_treatment_reference")]
    entities=sorted({str(e) for c in controls for e in c.get("entity_ids",[]) if e})
    return {"control_count":len(controls),"repeated_failure_control_count":len(repeated),"replacement_or_retransformation_count":len(transformed),"human_approved_control_count":len(approved),"evidence_bound_control_count":len(evidence),"missing_release103_scope_reference_count":len(scope_missing),"missing_root_cause_treatment_reference_count":len(root_missing),"affected_entity_ids":entities,"control_retransformation_ready":bool(transformed) and len(approved)==len(transformed) and not scope_missing and not root_missing,"automated_control_approval_allowed":False}

def cross_entity_deployment_sequence(payload: dict) -> dict:
    steps=payload.get("deployment_steps",[]); seq=[int(x.get("sequence",0) or 0) for x in steps if x.get("sequence") is not None]
    dup=sorted({n for n in seq if seq.count(n)>1}); unsat=[x for x in steps if x.get("dependency_ids") and not x.get("dependencies_satisfied",False)]; blocked=[x for x in steps if str(x.get("status","")).lower() in {"blocked","failed","overdue"}]
    approval=[x for x in steps if not x.get("human_sequence_approval_reference")]; scope=[x for x in steps if not x.get("release103_reauthorization_scope_reference")]
    entities=sorted({str(e) for x in steps for e in x.get("entity_ids",[]) if e})
    return {"deployment_step_count":len(steps),"entity_ids":entities,"cross_entity_scope":len(entities)>=2,"duplicate_sequence_numbers":dup,"unsatisfied_dependency_count":len(unsat),"blocked_step_count":len(blocked),"missing_human_sequence_approval_count":len(approval),"missing_release103_scope_reference_count":len(scope),"sequence_at_risk":bool(dup or unsat or blocked or approval or scope)}

def regulatory_commitment_alignment(payload: dict) -> dict:
    cs=payload.get("commitments",[]); aligned=[c for c in cs if c.get("mapped_remediation_workstream_id") and c.get("mapped_control_ids")]; ev=[c for c in cs if c.get("evidence_refs")]; overdue=[c for c in cs if str(c.get("status","")).lower() in {"overdue","breached","missed"}]; owner=[c for c in cs if not c.get("human_commitment_owner_confirmation_reference")]; ambiguity=[c for c in cs if c.get("requires_regulator_interpretation") and not c.get("human_regulatory_affairs_interpretation_reference")]
    return {"commitment_count":len(cs),"aligned_commitment_count":len(aligned),"evidence_bound_commitment_count":len(ev),"overdue_or_breached_commitment_count":len(overdue),"missing_human_owner_confirmation_count":len(owner),"unresolved_regulator_interpretation_count":len(ambiguity),"alignment_complete":bool(cs) and len(aligned)==len(cs) and not overdue and not owner and not ambiguity,"automated_commitment_closure_allowed":False}

def dependency_critical_path_assessment(payload: dict) -> dict:
    ms=payload.get("milestones",[]); critical=[m for m in ms if m.get("critical_path") is True]; blocked=[m for m in critical if str(m.get("status","")).lower() in {"blocked","failed","overdue"}]; unsat=[m for m in critical if m.get("dependency_ids") and not m.get("dependencies_satisfied",False)]; stale=[m for m in critical if not m.get("evidence_refs") or m.get("evidence_fresh") is False]
    return {"milestone_count":len(ms),"critical_path_count":len(critical),"blocked_critical_count":len(blocked),"critical_dependency_gap_count":len(unsat),"stale_or_missing_evidence_count":len(stale),"critical_path_at_risk":bool(blocked or unsat or stale)}

def implementation_drift_detection(payload: dict) -> dict:
    planned={str(x.get("control_id")):x for x in payload.get("planned_controls",[]) if x.get("control_id")}; actual={str(x.get("control_id")):x for x in payload.get("implemented_controls",[]) if x.get("control_id")}
    missing=sorted(set(planned)-set(actual)); design=sorted(k for k in set(planned)&set(actual) if str(planned[k].get("design_fingerprint",""))!=str(actual[k].get("design_fingerprint",""))); unauthorized=sorted(k for k,v in actual.items() if not v.get("human_control_retransformation_approval_reference")); scope=sorted(k for k,v in actual.items() if not v.get("release103_reauthorization_scope_reference")); root=sorted(k for k,v in actual.items() if not v.get("root_cause_treatment_reference")); entity=sorted(k for k in set(planned)&set(actual) if set(map(str,planned[k].get("entity_ids",[])))!=set(map(str,actual[k].get("entity_ids",[]))))
    score=min(100,len(missing)*20+len(design)*25+len(unauthorized)*30+len(scope)*25+len(root)*20+len(entity)*15)
    return {"missing_control_ids":missing,"design_drift_control_ids":design,"entity_scope_drift_control_ids":entity,"missing_human_approval_control_ids":unauthorized,"missing_release103_scope_control_ids":scope,"missing_root_cause_treatment_control_ids":root,"implementation_drift_score":score,"material_drift":score>=50,"human_review_required":bool(missing or design or entity or unauthorized or scope or root)}

def systemic_recovery_kpi_assessment(payload: dict) -> dict:
    ms=payload.get("metrics",[]); breached=[]; improved=0; evidence=0; enterprise=0
    for m in ms:
        a,t,b=m.get("actual"),m.get("target"),m.get("baseline"); direction=str(m.get("direction","higher_is_better")).lower()
        if m.get("evidence_ref"): evidence+=1
        if len(m.get("entity_ids",[]))>=2 or m.get("enterprise_metric") is True: enterprise+=1
        if a is not None and b is not None and ((direction=="lower_is_better" and float(a)<float(b)) or (direction!="lower_is_better" and float(a)>float(b))): improved+=1
        if a is not None and t is not None and ((direction=="lower_is_better" and float(a)>float(t)) or (direction!="lower_is_better" and float(a)<float(t))): breached.append(m)
    return {"metric_count":len(ms),"breached_metric_count":len(breached),"improved_vs_baseline_count":improved,"evidence_bound_metric_count":evidence,"enterprise_or_cross_entity_metric_count":enterprise,"systemic_recovery_kpi_score":round((len(ms)-len(breached))/len(ms)*100,2) if ms else 0.0,"systemic_recovery_target_met":bool(ms) and not breached and evidence==len(ms),"human_interpretation_required":True}

def independent_recovery_effectiveness_assurance(payload: dict) -> dict:
    ts=payload.get("tests",[]); failed=[t for t in ts if str(t.get("result","")).lower() in {"fail","failed","ineffective","regressed"}]
    independent=all(bool(t.get("independent_reviewer_id")) for t in ts) if ts else False; evidence=all(bool(t.get("evidence_refs")) for t in ts) if ts else False; release103=all(t.get("release103_reauthorization_scope_validated") is True for t in ts) if ts else False; roots=all(t.get("systemic_root_cause_treatment_validated") is True for t in ts) if ts else False; repeated=all(t.get("repeated_failure_scope_validated") is True for t in ts) if ts else False; cross=all(t.get("cross_entity_effectiveness_validated") is True for t in ts) if ts else False; sod=all(str(t.get("implementation_owner_id",""))!=str(t.get("independent_reviewer_id","")) for t in ts) if ts else False
    entities=sorted({str(e) for t in ts for e in t.get("entity_ids",[]) if e})
    return {"test_count":len(ts),"failed_test_count":len(failed),"validated_entity_ids":entities,"independence_complete":independent,"evidence_complete":evidence,"release103_reauthorization_scope_validated":release103,"systemic_root_cause_treatment_validated":roots,"repeated_failure_scope_validated":repeated,"cross_entity_effectiveness_validated":cross,"segregation_of_duties_satisfied":sod,"assurance_passed":bool(ts) and not failed and independent and evidence and release103 and roots and repeated and cross and sod,"human_certification_required":True,"automated_certification_allowed":False}

def enterprise_wide_control_validation(payload: dict) -> dict:
    vs=payload.get("control_validations",[]); ineffective=[v for v in vs if str(v.get("status","")).lower() in {"failed","ineffective","regressed","partial"}]; noent=[v for v in vs if not v.get("entity_ids")]; noev=[v for v in vs if not v.get("evidence_refs")]; noroot=[v for v in vs if not v.get("root_cause_treatment_validated")]; repeat=[v for v in vs if v.get("repeated_failure_control") and not v.get("repeated_failure_scope_validated")]; entities=sorted({str(e) for v in vs for e in v.get("entity_ids",[]) if e})
    return {"validation_count":len(vs),"validated_entity_ids":entities,"ineffective_validation_count":len(ineffective),"missing_entity_scope_count":len(noent),"missing_evidence_count":len(noev),"missing_root_cause_treatment_validation_count":len(noroot),"missing_repeated_failure_validation_count":len(repeat),"enterprise_validation_passed":bool(vs) and not ineffective and not noent and not noev and not noroot and not repeat and len(entities)>=2,"human_effectiveness_certification_required":True}

def blocker_escalation_assessment(payload: dict) -> dict:
    bs=payload.get("blockers",[]); material=[b for b in bs if str(b.get("severity","")).lower() in {"high","critical","material"}]; overdue=[b for b in bs if b.get("overdue") is True or str(b.get("status","")).lower() in {"overdue","breached"}]; cross=[b for b in bs if len(b.get("entity_ids",[]))>=2]; reg=[b for b in bs if b.get("regulatory_commitment_id") or b.get("regulator_followup_ref")]
    tier="executive_internal_audit" if material and (cross or reg) else "executive" if material or overdue else "operational"
    return {"blocker_count":len(bs),"material_blocker_count":len(material),"overdue_blocker_count":len(overdue),"cross_entity_blocker_count":len(cross),"regulatory_linked_blocker_count":len(reg),"recommended_escalation_tier":tier,"human_escalation_decision_required":bool(bs),"automated_program_reclosure_allowed":False}

def execution_readiness(payload: dict) -> dict:
    checks={k:bool(payload.get(k)) for k in ["release103_enterprise_remediation_reauthorization_reference_present","release103_human_reauthorization_confirmed","enterprise_remediation_workstreams_defined","systemic_root_cause_treatments_human_confirmed","systemic_control_retransformation_scope_human_approved","cross_entity_deployment_sequence_validated","regulatory_commitment_alignment_complete","critical_path_reviewed","implementation_evidence_current","systemic_recovery_kpis_baselined","independent_recovery_effectiveness_assurance_complete","enterprise_wide_control_validation_complete","material_blockers_resolved_or_human_escalated","executive_supervisory_review_complete"]}
    blockers=[k for k,v in checks.items() if not v]
    return {"execution_readiness_score":round(sum(checks.values())/len(checks)*100,2),"checks":checks,"blocking_items":blockers,"ready_for_human_enterprise_recovery_outcome_review":not blockers,"automated_certification_allowed":False,"automated_risk_acceptance_allowed":False,"automated_commitment_closure_allowed":False,"automated_program_reclosure_allowed":False}

def supervisory_dashboard_summary(payload: dict) -> dict:
    progress=remediation_program_progress(payload); blockers=blocker_escalation_assessment(payload); kpis=systemic_recovery_kpi_assessment(payload); roots=root_cause_treatment_mapping(payload)
    return {"progress":progress,"root_cause_treatment":roots,"blockers":blockers,"systemic_recovery_kpis":kpis,"supervisory_attention_required":progress["executive_attention_required"] or blockers["recommended_escalation_tier"]!="operational" or not kpis["systemic_recovery_target_met"] or not roots["treatment_mapping_complete"],"monitoring_only":True}

def audit_export_manifest(payload: dict) -> dict:
    refs=sorted({str(x) for x in payload.get("version_refs",[]) if x}); ev=sorted({str(x) for x in payload.get("evidence_refs",[]) if x}); body={"version_refs":refs,"evidence_refs":ev,"tenant_id":payload.get("tenant_id"),"remediation_program_id":payload.get("remediation_program_id")}
    return {**body,"manifest_hash":version_hash(body),"immutable_export":True,"human_submission_required":True}
