from app.domain.regulatory_examination_enterprise_intervention_sustainability import ENTERPRISE_INTERVENTION_SUSTAINABILITY_AUTHORITY, enterprise_intervention_sustainability_contract
from app.evaluation.regulatory_examination_enterprise_intervention_sustainability import systemic_risk_reduction, sustainability_assurance, intervention_closure_readiness, recurrence_reopen_signal
from app.services.regulatory_examination_enterprise_intervention_sustainability import RegulatoryExaminationEnterpriseInterventionSustainabilityService


def test_release75_non_delegable_authority():
    a=ENTERPRISE_INTERVENTION_SUSTAINABILITY_AUTHORITY
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_sustainability"] is False
    assert a["ai_can_close_intervention_program"] is False
    assert a["worker_can_close_intervention_program"] is False


def test_release75_risk_reduction_and_sustainability():
    r=systemic_risk_reduction({"baseline_systemic_risk_score":80,"post_remediation_systemic_risk_score":20,"minimum_reduction_percent":50})
    assert r["risk_reduction_percent"]==75 and r["target_met"]
    s=sustainability_assurance({"required_entity_ids":["US","EU"],"sustainability_window_complete":True,"sustainability_observations":[{"entity_id":"US","control_effective":True,"recurrence_detected":False},{"entity_id":"EU","control_effective":True,"recurrence_detected":False}]})
    assert s["eligible_for_human_closure_review"] and s["automated_closure_allowed"] is False


def test_release75_closure_gate_and_reopen_signal():
    ready=intervention_closure_readiness({"implementation_complete":True,"independent_effectiveness_passed":True,"sustainability_assurance_passed":True,"cross_entity_reconciled":True,"regulatory_commitments_reconciled":True,"unresolved_blocker_count":0,"residual_risk_accepted_by_human":True})
    assert ready["closure_readiness_score"]==100 and ready["ready_for_human_executive_closure"]
    blocked=intervention_closure_readiness({"implementation_complete":True,"independent_effectiveness_passed":True,"sustainability_assurance_passed":True,"cross_entity_reconciled":True,"regulatory_commitments_reconciled":True,"unresolved_blocker_count":1,"residual_risk_accepted_by_human":True})
    assert not blocked["ready_for_human_executive_closure"]
    sig=recurrence_reopen_signal({"control_health_decay_percent":35,"control_health_decay_threshold_percent":20})
    assert sig["reopen_candidate"] and sig["automated_reopen_allowed"] is False


def test_release75_human_risk_acceptance_and_closure():
    s=RegulatoryExaminationEnterpriseInterventionSustainabilityService(None,"tenant-a")
    try: s.accept_residual_risk("ai",{"intervention_program_id":"p1","reviewer_role":"ai_agent","decision":"accept","residual_systemic_risk_score":10,"rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot accept residual systemic risk")
    rr=s.accept_residual_risk("cro",{"intervention_program_id":"p1","reviewer_role":"chief_risk_officer","decision":"accept","residual_systemic_risk_score":10,"rationale":"within approved appetite","evidence_refs":["ev1"]})
    ass=s.sustainability_assurance("audit",{"intervention_program_id":"p1","reviewer_role":"internal_auditor","required_entity_ids":["US"],"sustainability_observations":[{"entity_id":"US","control_effective":True,"recurrence_detected":False}],"sustainability_window_complete":True,"rationale":"sustained"})
    try: s.executive_closure("ai",{"intervention_program_id":"p1","reviewer_role":"ai_agent","decision":"close","rationale":"x","residual_risk_acceptance_version_id":rr["residual_risk_acceptance_version_id"],"sustainability_assurance_version_id":ass["sustainability_assurance_version_id"],"closure_readiness_score":100})
    except PermissionError: pass
    else: raise AssertionError("AI cannot close program")
    closed=s.executive_closure("exec",{"intervention_program_id":"p1","reviewer_role":"executive_certifier","decision":"close","rationale":"all gates met","residual_risk_acceptance_version_id":rr["residual_risk_acceptance_version_id"],"sustainability_assurance_version_id":ass["sustainability_assurance_version_id"],"closure_readiness_score":100,"evidence_refs":["ev1"]})
    assert closed["human_decision"] and closed["automated_closure"] is False
    assert "human risk acceptance" in enterprise_intervention_sustainability_contract()["traceability"]
