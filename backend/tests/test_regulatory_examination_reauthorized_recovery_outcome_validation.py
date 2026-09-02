from app.domain.regulatory_examination_reauthorized_recovery_outcome_validation import REAUTHORIZED_RECOVERY_OUTCOME_AUTHORITY,reauthorized_recovery_outcome_contract
from app.evaluation.regulatory_examination_reauthorized_recovery_outcome_validation import cross_entity_completion,independent_recovery_outcome_assurance,reclosure_readiness,repeated_failure_control_effectiveness,sustainability_assessment,systemic_risk_reduction
from app.services.regulatory_examination_reauthorized_recovery_outcome_validation import RegulatoryExaminationReauthorizedRecoveryOutcomeValidationService

def test_release89_non_delegable_authority():
    a=REAUTHORIZED_RECOVERY_OUTCOME_AUTHORITY
    assert not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"] and not a["ai_can_recertify_recovery"] and not a["ai_can_reclose_program"]
    assert not a["worker_can_reclose_program"] and a["independent_outcome_validation_required"]

def test_release89_risk_repeated_failure_and_cross_entity_validation():
    risk=systemic_risk_reduction({"baseline_systemic_risk_score":90,"current_systemic_risk_score":45,"minimum_required_reduction_percent":30})
    assert risk["risk_reduction_percent"]==50.0 and risk["risk_reduction_target_met"]
    repeated=repeated_failure_control_effectiveness({"controls":[{"control_id":"c1","failure_count":3,"result":"pass","evidence_refs":["e1"]},{"control_id":"c2","repeated_failure":True,"effectiveness":"stable","evidence_refs":["e2"]}]})
    assert repeated["repeated_failure_controls_effective"] and repeated["validated_effective_count"]==2
    entities=cross_entity_completion({"entities":[{"entity_id":"US","status":"complete","evidence_refs":["e1"],"repeated_failure_scope_validated":True},{"entity_id":"EU","status":"validated","evidence_refs":["e2"],"repeated_failure_scope_validated":True}]})
    assert entities["cross_entity_completion_reconciled"]

def test_release89_independent_sustainability_and_readiness():
    iv=independent_recovery_outcome_assurance({"tests":[{"result":"pass","independent_reviewer_id":"ia1","evidence_refs":["ev1"],"repeated_failure_scope_validated":True}]})
    assert iv["independent_recovery_outcome_validated"] and not iv["automated_certification_allowed"]
    sustain=sustainability_assessment({"observed_window_days":90,"minimum_window_days":60,"minimum_control_health_score":85,"observations":[{"status":"stable","control_health_score":93}]})
    assert sustain["sustainability_assurance_passed"]
    ready=reclosure_readiness({"reauthorized_recovery_outcomes_complete":True,"cross_entity_completion_reconciled":True,"repeated_failure_controls_effective":True,"independent_recovery_outcome_validated":True,"systemic_risk_reduction_verified":True,"unresolved_blockers_cleared":True,"regulatory_commitments_reconciled":True,"sustainability_window_passed":True,"residual_risk_human_decision_recorded":True})
    assert ready["ready_for_executive_recertification"] and ready["reclosure_readiness_score"]==100.0

def test_release89_human_recertification_and_reclosure_boundaries():
    svc=RegulatoryExaminationReauthorizedRecoveryOutcomeValidationService(None,"tenant-a")
    try: svc.residual_risk_reassessment("ai",{"actor_role":"ai_agent","decision":"accept","residual_systemic_risk_score":8,"rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot accept residual systemic risk")
    try: svc.reclose_program("ai",{"actor_role":"ai_agent","decision":"reclose","recovery_recertification_version_id":"rr1","rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot reclose program")
    cert=svc.recertify_recovery("cro",{"actor_role":"chief_risk_officer","decision":"recertify","independent_outcome_validation_version_id":"iv1","residual_risk_decision_version_id":"rv1","sustainability_assessment_version_id":"sv1","rationale":"evidence complete"})
    assert cert["human_decision"] and not cert["automated_recertification"]
    assert "executive recovery recertification" in reauthorized_recovery_outcome_contract()["traceability"]
