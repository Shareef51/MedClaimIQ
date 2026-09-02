from app.domain.regulatory_examination_systemic_failure_investigation import SYSTEMIC_FAILURE_INVESTIGATION_AUTHORITY, systemic_failure_investigation_contract
from app.evaluation.regulatory_examination_systemic_failure_investigation import reconstruct_multi_cycle_evidence, validate_prior_assumptions, reassess_root_causes, analyze_failed_control_redesign, remediation_reauthorization_readiness
from app.services.regulatory_examination_systemic_failure_investigation import RegulatoryExaminationSystemicFailureInvestigationService

def test_release79_non_delegable_authority():
    a=SYSTEMIC_FAILURE_INVESTIGATION_AUTHORITY
    assert a["ai_can_authorize_remediation"] is False
    assert a["ai_can_approve_intervention_program"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_controls"] is False
    assert a["worker_can_authorize_remediation"] is False

def test_release79_evidence_assumptions_and_root_cause_reassessment():
    e=reconstruct_multi_cycle_evidence({"cycles":[{"cycle_id":"c1","evidence_refs":["e1"]},{"cycle_id":"c2","evidence_refs":["e2"]}]})
    assert e["evidence_complete"] and e["unique_evidence_count"]==2
    a=validate_prior_assumptions({"assumptions":[{"id":"a1","status":"invalid"},{"id":"a2","status":"valid"}]})
    assert a["prior_remediation_assumptions_at_risk"] and a["invalid_assumption_count"]==1
    r=reassess_root_causes({"prior_root_cause_ids":["r1"],"current_root_cause_ids":["r1","r2"],"control_redesign_failed":True})
    assert r["persistent_root_cause_pattern"] and "r2" in r["new_root_cause_ids"]

def test_release79_failed_control_redesign_and_readiness():
    c=analyze_failed_control_redesign({"controls":[{"id":"c1","redesign_effective":False,"entity_ids":["US"]},{"id":"c2","retest_passed":False,"entity_ids":["EU"]}]})
    assert c["enterprise_control_redesign_failure"] and len(c["affected_entity_ids"])==2
    ready=remediation_reauthorization_readiness({"evidence_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_scope_validated":True,"independent_challenge_complete":True,"regulator_follow_up_assessed":True,"renewed_strategy_documented":True})
    assert ready["ready_for_human_authorization"] and ready["reauthorization_readiness_score"]==100

def test_release79_human_authorization_boundaries():
    svc=RegulatoryExaminationSystemicFailureInvestigationService(None,"tenant-a")
    try: svc.independent_challenge("ai",{"intervention_program_id":"p1","reviewer_role":"ai_agent","decision":"agree","rationale":"x","evidence_refs":[]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot perform independent challenge")
    readiness={"evidence_reconstructed":True,"root_cause_human_confirmed":True,"cross_entity_scope_validated":True,"independent_challenge_complete":True,"regulator_follow_up_assessed":True,"renewed_strategy_documented":True}
    try: svc.authorize_remediation("ai",{"intervention_program_id":"p1","actor_role":"ai_agent","decision":"authorize","rationale":"x","readiness":readiness,"evidence_refs":[]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot authorize remediation")
    result=svc.authorize_remediation("cro",{"intervention_program_id":"p1","actor_role":"chief_risk_officer","decision":"authorize","rationale":"human approval","readiness":readiness,"evidence_refs":["e1"]})
    assert result["human_authorization"] and not result["automated_authorization"]
    assert "human authorization" in systemic_failure_investigation_contract()["traceability"]
