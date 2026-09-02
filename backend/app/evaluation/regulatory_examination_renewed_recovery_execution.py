from __future__ import annotations
import hashlib,json

def version_hash(payload:dict)->str: return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()

def program_progress(payload:dict)->dict:
 workstreams=payload.get("workstreams",[]); total=len(workstreams); completed=sum(1 for x in workstreams if str(x.get("status","")).lower() in {"complete","completed","done"}); blocked=[x for x in workstreams if str(x.get("status","")).lower() in {"blocked","overdue","failed"}]
 pct=round(completed/total*100,2) if total else 0.0
 return {"workstream_count":total,"completed_workstream_count":completed,"blocked_workstream_count":len(blocked),"progress_percent":pct,"executive_attention_required":bool(blocked)}

def control_rehabilitation_status(payload:dict)->dict:
 controls=payload.get("controls",[]); failed=[c for c in controls if str(c.get("status","")).lower() in {"failed","ineffective","degraded"}]; replaced=[c for c in controls if str(c.get("action","")).lower() in {"replace","replaced","redesign","rehabilitate"} and c.get("implementation_evidence_refs")]
 entities=sorted({str(e) for c in controls for e in c.get("entity_ids",[]) if e})
 return {"control_count":len(controls),"failed_control_count":len(failed),"evidence_bound_rehabilitation_count":len(replaced),"affected_entity_ids":entities,"human_approval_required":bool(replaced or failed),"automated_control_approval_allowed":False}

def critical_path_assessment(payload:dict)->dict:
 milestones=payload.get("milestones",[]); blocked=[m for m in milestones if str(m.get("status","")).lower() in {"blocked","overdue","failed"}]; critical=[m for m in milestones if m.get("critical_path") is True]; missing=[m for m in milestones if m.get("critical_path") is True and not m.get("evidence_refs")]
 return {"milestone_count":len(milestones),"critical_path_count":len(critical),"blocked_milestone_count":len(blocked),"critical_path_missing_evidence_count":len(missing),"critical_path_at_risk":bool(blocked or missing)}

def implementation_drift(payload:dict)->dict:
 planned=payload.get("planned_controls",[]); actual=payload.get("implemented_controls",[]); p={str(x.get("control_id")):x for x in planned if x.get("control_id")}; a={str(x.get("control_id")):x for x in actual if x.get("control_id")}; missing=sorted(set(p)-set(a)); changed=sorted(k for k in set(p)&set(a) if str(p[k].get("design_fingerprint",""))!=str(a[k].get("design_fingerprint","")))
 score=min(100,len(missing)*35+len(changed)*25)
 return {"missing_control_ids":missing,"design_drift_control_ids":changed,"implementation_drift_score":score,"material_drift":score>=50,"human_review_required":bool(missing or changed)}

def recovery_kpis(payload:dict)->dict:
 metrics=payload.get("metrics",[]); breached=[m for m in metrics if m.get("target") is not None and m.get("actual") is not None and float(m.get("actual")) < float(m.get("target"))]
 achieved=len(metrics)-len(breached); score=round(achieved/len(metrics)*100,2) if metrics else 0.0
 return {"metric_count":len(metrics),"breached_metric_count":len(breached),"recovery_kpi_score":score,"recovery_target_met":bool(metrics) and not breached,"human_interpretation_required":True}

def independent_revalidation(payload:dict)->dict:
 tests=payload.get("tests",[]); passed=[t for t in tests if str(t.get("result","")).lower() in {"pass","passed","effective"}]; failed=[t for t in tests if str(t.get("result","")).lower() in {"fail","failed","ineffective"}]; entities=sorted({str(e) for t in tests for e in t.get("entity_ids",[]) if e}); independent=all(bool(t.get("independent_reviewer_id")) for t in tests) if tests else False
 return {"test_count":len(tests),"passed_test_count":len(passed),"failed_test_count":len(failed),"validated_entity_ids":entities,"independence_complete":independent,"revalidation_passed":bool(tests) and not failed and independent,"human_certification_required":True,"automated_certification_allowed":False}

def execution_readiness(payload:dict)->dict:
 checks={"human_authorization_reference_present":bool(payload.get("human_authorization_reference_present")),"program_workstreams_defined":bool(payload.get("program_workstreams_defined")),"control_rehabilitation_scope_approved":bool(payload.get("control_rehabilitation_scope_approved")),"commitment_mapping_complete":bool(payload.get("commitment_mapping_complete")),"critical_path_reviewed":bool(payload.get("critical_path_reviewed")),"execution_evidence_current":bool(payload.get("execution_evidence_current")),"independent_revalidation_complete":bool(payload.get("independent_revalidation_complete"))}
 blockers=[k for k,v in checks.items() if not v]; score=round(sum(checks.values())/len(checks)*100,2)
 return {"execution_readiness_score":score,"checks":checks,"blocking_items":blockers,"ready_for_human_outcome_review":not blockers,"automated_certification_allowed":False}
