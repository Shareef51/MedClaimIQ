from app.evaluation.regulatory_examination_reopened_recovery_investigation import validate_prior_recovery_assumptions,reassess_decay_root_causes,analyze_cross_entity_control_gaps,regulator_follow_up_impact
def run_reopened_recovery_investigation_monitor(items:list[dict])->dict:
 alerts=[]
 for item in items:
  a=validate_prior_recovery_assumptions(item); r=reassess_decay_root_causes(item); g=analyze_cross_entity_control_gaps(item); f=regulator_follow_up_impact(item)
  if a["prior_recovery_assumptions_at_risk"] or r["persistent_root_cause_pattern"] or g["enterprise_control_gap"] or f["renewed_remediation_impact"]:
   alerts.append({"intervention_program_id":item.get("intervention_program_id"),"human_investigation_required":True,"worker_authorization_authority":False,"assumptions_at_risk":a["prior_recovery_assumptions_at_risk"],"persistent_root_cause_pattern":r["persistent_root_cause_pattern"],"enterprise_control_gap":g["enterprise_control_gap"],"regulator_follow_up_impact":f["renewed_remediation_impact"]})
 return {"monitoring_only":True,"automated_remediation_authorization":False,"automated_risk_acceptance":False,"automated_recovery_certification":False,"alerts":alerts}
