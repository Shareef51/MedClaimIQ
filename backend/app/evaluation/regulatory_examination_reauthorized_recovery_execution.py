from __future__ import annotations
import hashlib,json

def version_hash(payload:dict)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()

def reauthorized_program_progress(payload:dict)->dict:
    workstreams=payload.get("workstreams",[]); total=len(workstreams)
    completed=sum(1 for x in workstreams if str(x.get("status","")).lower() in {"complete","completed","done"})
    blocked=[x for x in workstreams if str(x.get("status","")).lower() in {"blocked","overdue","failed"}]
    repeated=[x for x in workstreams if bool(x.get("repeated_failure_scope"))]
    pct=round(completed/total*100,2) if total else 0.0
    return {"workstream_count":total,"completed_workstream_count":completed,"blocked_workstream_count":len(blocked),"repeated_failure_workstream_count":len(repeated),"progress_percent":pct,"executive_attention_required":bool(blocked)}

def control_rerehabilitation_status(payload:dict)->dict:
    controls=payload.get("controls",[])
    repeated=[c for c in controls if bool(c.get("repeated_failure")) or int(c.get("failure_count",0) or 0)>=2]
    replacements=[c for c in controls if str(c.get("action","")).lower() in {"replace","replacement","redesign","re-rehabilitate","rerehabilitate"}]
    evidence_bound=[c for c in replacements if c.get("implementation_evidence_refs")]
    unapproved=[c for c in replacements if not c.get("human_approval_reference")]
    entities=sorted({str(e) for c in controls for e in c.get("entity_ids",[]) if e})
    return {"control_count":len(controls),"repeated_failure_control_count":len(repeated),"replacement_or_rerehabilitation_count":len(replacements),"evidence_bound_control_count":len(evidence_bound),"missing_human_approval_count":len(unapproved),"affected_entity_ids":entities,"human_approval_required":bool(replacements),"automated_control_approval_allowed":False}

def deployment_sequence_assessment(payload:dict)->dict:
    steps=payload.get("deployment_steps",[])
    seq=[int(x.get("sequence",0) or 0) for x in steps if x.get("sequence") is not None]
    duplicates=sorted({x for x in seq if seq.count(x)>1})
    blocked=[x for x in steps if str(x.get("status","")).lower() in {"blocked","failed","overdue"}]
    dependency_gaps=[x for x in steps if x.get("dependency_ids") and not x.get("dependencies_satisfied",False)]
    entities=sorted({str(e) for x in steps for e in x.get("entity_ids",[]) if e})
    return {"deployment_step_count":len(steps),"duplicate_sequence_numbers":duplicates,"blocked_step_count":len(blocked),"unsatisfied_dependency_count":len(dependency_gaps),"entity_ids":entities,"sequence_at_risk":bool(duplicates or blocked or dependency_gaps)}

def critical_path_assessment(payload:dict)->dict:
    milestones=payload.get("milestones",[])
    critical=[m for m in milestones if m.get("critical_path") is True]
    blocked=[m for m in critical if str(m.get("status","")).lower() in {"blocked","overdue","failed"}]
    stale=[m for m in critical if not m.get("evidence_refs") or m.get("evidence_fresh") is False]
    return {"milestone_count":len(milestones),"critical_path_count":len(critical),"blocked_critical_count":len(blocked),"stale_or_missing_evidence_count":len(stale),"critical_path_at_risk":bool(blocked or stale)}

def implementation_drift(payload:dict)->dict:
    planned=payload.get("planned_controls",[]); actual=payload.get("implemented_controls",[])
    p={str(x.get("control_id")):x for x in planned if x.get("control_id")}; a={str(x.get("control_id")):x for x in actual if x.get("control_id")}
    missing=sorted(set(p)-set(a)); changed=sorted(k for k in set(p)&set(a) if str(p[k].get("design_fingerprint",""))!=str(a[k].get("design_fingerprint","")))
    unauthorized=sorted(k for k,v in a.items() if v.get("human_approval_reference") in {None,""})
    score=min(100,len(missing)*30+len(changed)*25+len(unauthorized)*35)
    return {"missing_control_ids":missing,"design_drift_control_ids":changed,"missing_human_approval_control_ids":unauthorized,"implementation_drift_score":score,"material_drift":score>=50,"human_review_required":bool(missing or changed or unauthorized)}

def recovery_kpi_assessment(payload:dict)->dict:
    metrics=payload.get("metrics",[]); breached=[]; improved=0
    for m in metrics:
        actual=m.get("actual"); target=m.get("target"); baseline=m.get("baseline")
        direction=str(m.get("direction","higher_is_better")).lower()
        if actual is not None and baseline is not None:
            if (direction=="lower_is_better" and float(actual)<float(baseline)) or (direction!="lower_is_better" and float(actual)>float(baseline)): improved+=1
        if actual is not None and target is not None:
            fail=(direction=="lower_is_better" and float(actual)>float(target)) or (direction!="lower_is_better" and float(actual)<float(target))
            if fail: breached.append(m)
    score=round((len(metrics)-len(breached))/len(metrics)*100,2) if metrics else 0.0
    return {"metric_count":len(metrics),"breached_metric_count":len(breached),"improved_vs_baseline_count":improved,"recovery_kpi_score":score,"recovery_target_met":bool(metrics) and not breached,"human_interpretation_required":True}

def independent_recovery_assurance(payload:dict)->dict:
    tests=payload.get("tests",[])
    failed=[t for t in tests if str(t.get("result","")).lower() in {"fail","failed","ineffective"}]
    independent=all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
    repeated_scoped=all(t.get("repeated_failure_scope_validated") is True for t in tests) if tests else False
    entities=sorted({str(e) for t in tests for e in t.get("entity_ids",[]) if e})
    return {"test_count":len(tests),"failed_test_count":len(failed),"validated_entity_ids":entities,"independence_complete":independent,"repeated_failure_scope_validated":repeated_scoped,"assurance_passed":bool(tests) and not failed and independent and repeated_scoped,"human_certification_required":True,"automated_certification_allowed":False}

def execution_readiness(payload:dict)->dict:
    checks={
        "human_reauthorization_reference_present":bool(payload.get("human_reauthorization_reference_present")),
        "reauthorized_workstreams_defined":bool(payload.get("reauthorized_workstreams_defined")),
        "control_rerehabilitation_scope_human_approved":bool(payload.get("control_rerehabilitation_scope_human_approved")),
        "cross_entity_sequence_validated":bool(payload.get("cross_entity_sequence_validated")),
        "regulatory_commitment_alignment_complete":bool(payload.get("regulatory_commitment_alignment_complete")),
        "critical_path_reviewed":bool(payload.get("critical_path_reviewed")),
        "execution_evidence_current":bool(payload.get("execution_evidence_current")),
        "independent_recovery_assurance_complete":bool(payload.get("independent_recovery_assurance_complete")),
    }
    blockers=[k for k,v in checks.items() if not v]; score=round(sum(checks.values())/len(checks)*100,2)
    return {"execution_readiness_score":score,"checks":checks,"blocking_items":blockers,"ready_for_human_outcome_review":not blockers,"automated_certification_allowed":False,"automated_risk_acceptance_allowed":False}
