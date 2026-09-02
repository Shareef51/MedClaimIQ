from app.evaluation.regulatory_examination_reauthorized_recovery_execution import deployment_sequence_assessment,critical_path_assessment,implementation_drift,recovery_kpi_assessment,independent_recovery_assurance

def run_reauthorized_recovery_execution_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        s=deployment_sequence_assessment(item); c=critical_path_assessment(item); d=implementation_drift(item); k=recovery_kpi_assessment(item); a=independent_recovery_assurance(item)
        if s["sequence_at_risk"] or c["critical_path_at_risk"] or d["material_drift"] or (k["metric_count"] and not k["recovery_target_met"]) or (a["test_count"] and not a["assurance_passed"]):
            alerts.append({"recovery_program_id":item.get("recovery_program_id"),"human_review_required":True,"sequence_at_risk":s["sequence_at_risk"],"critical_path_at_risk":c["critical_path_at_risk"],"material_drift":d["material_drift"],"recovery_target_met":k["recovery_target_met"],"independent_assurance_passed":a["assurance_passed"]})
    return {"monitoring_only":True,"automated_control_approval":False,"automated_recovery_certification":False,"automated_risk_acceptance":False,"automated_commitment_closure":False,"automated_program_reclosure":False,"alerts":alerts}
