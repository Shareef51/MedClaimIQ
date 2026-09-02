from app.evaluation.regulatory_examination_systemic_failure_investigation import validate_prior_assumptions, reassess_root_causes, analyze_failed_control_redesign, regulator_follow_up_impact

def run_systemic_failure_investigation_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        assumptions=validate_prior_assumptions(item); roots=reassess_root_causes(item); controls=analyze_failed_control_redesign(item); followup=regulator_follow_up_impact(item)
        if assumptions["prior_remediation_assumptions_at_risk"] or roots["persistent_root_cause_pattern"] or controls["enterprise_control_redesign_failure"] or followup["renewed_strategy_impact"]:
            alerts.append({"intervention_program_id":item.get("intervention_program_id"),"assumptions_at_risk":assumptions["prior_remediation_assumptions_at_risk"],"persistent_root_cause_pattern":roots["persistent_root_cause_pattern"],"enterprise_control_redesign_failure":controls["enterprise_control_redesign_failure"],"regulator_follow_up_impact":followup["renewed_strategy_impact"],"human_investigation_required":True,"worker_authorization_authority":False})
    return {"monitoring_only":True,"automated_remediation_authorization":False,"automated_risk_acceptance":False,"automated_control_certification":False,"alerts":alerts}
