from app.evaluation.regulatory_examination_repeated_recovery_failure_investigation import reconstruct_recovery_cycles,validate_recovery_assumptions,reassess_recovery_root_causes,analyze_failed_rehabilitation,regulator_recovery_impact
def run_repeated_recovery_failure_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        cycles=reconstruct_recovery_cycles(item); assumptions=validate_recovery_assumptions(item); roots=reassess_recovery_root_causes(item); rehab=analyze_failed_rehabilitation(item); follow=regulator_recovery_impact(item)
        if cycles["repeated_failure"] or assumptions["prior_recovery_assumptions_at_risk"] or roots["persistent_recovery_failure_pattern"] or rehab["enterprise_rehabilitation_failure"] or follow["renewed_recovery_strategy_impact"]:
            alerts.append({"recovery_program_id":item.get("recovery_program_id"),"repeated_failure":cycles["repeated_failure"],"assumptions_at_risk":assumptions["prior_recovery_assumptions_at_risk"],"persistent_root_cause_pattern":roots["persistent_recovery_failure_pattern"],"enterprise_rehabilitation_failure":rehab["enterprise_rehabilitation_failure"],"regulator_follow_up_impact":follow["renewed_recovery_strategy_impact"],"human_investigation_required":True,"worker_authorization_authority":False})
    return {"monitoring_only":True,"automated_remediation_authorization":False,"automated_risk_acceptance":False,"automated_recovery_certification":False,"alerts":alerts}
