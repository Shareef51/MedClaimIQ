from app.domain.regulatory_examination_repeated_recovery_failure_investigation import REPEATED_RECOVERY_FAILURE_INVESTIGATION_AUTHORITY,repeated_recovery_failure_investigation_contract
from app.evaluation.regulatory_examination_repeated_recovery_failure_investigation import reconstruct_recovery_cycles,reassess_recovery_root_causes,analyze_failed_rehabilitation,remediation_reauthorization_readiness
from app.services.regulatory_examination_repeated_recovery_failure_investigation import RegulatoryExaminationRepeatedRecoveryFailureInvestigationService
def test_release87_non_delegable_authority():
    a=REPEATED_RECOVERY_FAILURE_INVESTIGATION_AUTHORITY
    assert not a["ai_can_authorize_remediation"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"] and not a["worker_can_authorize_remediation"]
def test_release87_reconstruct_and_reassess():
    r=reconstruct_recovery_cycles({"cycles":[{"cycle_id":"1","status":"failed","evidence_refs":["e1"]},{"cycle_id":"2","status":"recurred","evidence_refs":["e2"]}]})
    assert r["repeated_failure"] and r["evidence_complete"]
    rc=reassess_recovery_root_causes({"prior_root_cause_ids":["rc1"],"current_root_cause_ids":["rc1","rc2"],"rehabilitation_failed":True,"risk_rebound_detected":True})
    assert rc["persistent_recovery_failure_pattern"] and rc["root_cause_reassessment_score"]>=60
def test_release87_failed_rehabilitation_and_readiness():
    c=analyze_failed_rehabilitation({"controls":[{"rehabilitation_effective":False,"entity_ids":["US"]},{"revalidation_passed":False,"entity_ids":["EU"]}]})
    assert c["enterprise_rehabilitation_failure"]
    ready=remediation_reauthorization_readiness({"recovery_evidence_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_scope_validated":True,"failed_rehabilitation_assessed":True,"independent_internal_audit_challenge_complete":True,"regulator_follow_up_assessed":True,"renewed_recovery_strategy_documented":True})
    assert ready["ready_for_human_authorization"] and not ready["automated_authorization_allowed"]
def test_release87_human_reauthorization_boundary():
    svc=RegulatoryExaminationRepeatedRecoveryFailureInvestigationService(None,"tenant-a")
    readiness={"recovery_evidence_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_scope_validated":True,"failed_rehabilitation_assessed":True,"independent_internal_audit_challenge_complete":True,"regulator_follow_up_assessed":True,"renewed_recovery_strategy_documented":True}
    try: svc.authorize_remediation("ai",{"actor_role":"ai_agent","decision":"authorize","rationale":"x","readiness":readiness})
    except PermissionError: pass
    else: raise AssertionError("AI cannot authorize renewed remediation")
    auth=svc.authorize_remediation("cro",{"actor_role":"chief_risk_officer","decision":"authorize","rationale":"human authorization","readiness":readiness})
    assert auth["human_authorization"] and not auth["automated_authorization"]
    assert "human remediation reauthorization" in repeated_recovery_failure_investigation_contract()["traceability"]
