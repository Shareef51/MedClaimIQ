from app.evaluation.regulatory_examination_renewed_recovery_execution import critical_path_assessment,implementation_drift,recovery_kpis,independent_revalidation

def run_renewed_recovery_execution_monitor(items:list[dict])->dict:
 alerts=[]
 for item in items:
  c=critical_path_assessment(item); d=implementation_drift(item); k=recovery_kpis(item); r=independent_revalidation(item)
  if c["critical_path_at_risk"] or d["material_drift"] or (k["metric_count"] and not k["recovery_target_met"]) or (r["test_count"] and not r["revalidation_passed"]):
   alerts.append({"intervention_program_id":item.get("intervention_program_id"),"human_review_required":True,"critical_path_at_risk":c["critical_path_at_risk"],"material_drift":d["material_drift"],"recovery_target_met":k["recovery_target_met"],"independent_revalidation_passed":r["revalidation_passed"]})
 return {"monitoring_only":True,"automated_control_approval":False,"automated_recovery_certification":False,"automated_risk_acceptance":False,"automated_program_reclosure":False,"alerts":alerts}
