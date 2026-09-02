from app.evaluation.regulatory_examination_reauthorized_recovery_outcome_validation import reauthorized_recovery_outcomes,repeated_failure_control_effectiveness,regulatory_commitment_completion,sustainability_assessment,systemic_risk_reduction

def run_reauthorized_recovery_outcome_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        outcomes=reauthorized_recovery_outcomes(item); repeated=repeated_failure_control_effectiveness(item); risk=systemic_risk_reduction(item); commitments=regulatory_commitment_completion(item); sustainability=sustainability_assessment(item)
        if outcomes["blocked_workstream_count"] or outcomes["failed_control_count"] or repeated["failed_or_degraded_count"] or (risk["baseline_systemic_risk_score"] and not risk["risk_reduction_target_met"]) or commitments["unresolved_commitment_ids"] or (sustainability["observation_count"] and not sustainability["sustainability_assurance_passed"]):
            alerts.append({"recovery_program_id":item.get("recovery_program_id"),"human_review_required":True,"blocked_workstream_count":outcomes["blocked_workstream_count"],"failed_control_count":outcomes["failed_control_count"],"repeated_failure_controls_effective":repeated["repeated_failure_controls_effective"],"risk_reduction_target_met":risk["risk_reduction_target_met"],"unresolved_commitment_ids":commitments["unresolved_commitment_ids"],"sustainability_assurance_passed":sustainability["sustainability_assurance_passed"]})
    return {"monitoring_only":True,"automated_risk_acceptance":False,"automated_recovery_certification":False,"automated_commitment_closure":False,"automated_program_reclosure":False,"alerts":alerts}
