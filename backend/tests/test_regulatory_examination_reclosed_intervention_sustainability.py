from app.domain.regulatory_examination_reclosed_intervention_sustainability import RECLOSED_INTERVENTION_SUSTAINABILITY_AUTHORITY, reclosed_intervention_sustainability_contract
from app.evaluation.regulatory_examination_reclosed_intervention_sustainability import sustainability_health, multi_cycle_recurrence, prior_reclosure_comparison, cross_entity_propagation, enterprise_materiality
from app.services.regulatory_examination_reclosed_intervention_sustainability import RegulatoryExaminationReclosedInterventionSustainabilityService


def test_release78_non_delegable_authority():
    a=RECLOSED_INTERVENTION_SUSTAINABILITY_AUTHORITY
    assert a["ai_can_reopen_or_reclose_program"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_effectiveness"] is False
    assert a["worker_can_reopen_or_reclose"] is False


def test_release78_multi_cycle_decay_and_propagation():
    h=sustainability_health({"baseline_control_health":95,"current_control_health":70,"minimum_control_health":80,"material_decay_threshold":15})
    assert h["sustainability_at_risk"] and h["control_health_decay"]==25
    r=multi_cycle_recurrence({"cycles":[{"examination_id":"e1","confirmed_recurrence":True,"intervention_effective":False,"entity_ids":["US"]},{"examination_id":"e2","confirmed_recurrence":True,"intervention_effective":False,"entity_ids":["EU"]}]})
    assert r["repeated_systemic_failure"] and r["executive_review_required"] and r["internal_audit_review_required"]
    p=cross_entity_propagation({"in_scope_entity_ids":["US","EU","APAC"],"observed_entity_ids":["US","EU"]})
    assert p["enterprise_propagation"] and p["impacted_entity_count"]==2


def test_release78_prior_reclosure_and_materiality():
    c=prior_reclosure_comparison({"root_cause_ids":["r1"],"control_ids":["c1"],"residual_systemic_risk_score":15},{"root_cause_ids":["r1","r2"],"control_ids":["c1"],"current_systemic_risk_score":48})
    assert c["same_failure_pattern"] and c["systemic_risk_rebound"]==33
    m=enterprise_materiality({"multi_cycle_recurrence_score":80,"propagation_ratio":0.75,"systemic_risk_rebound":25,"regulatory_follow_up_risk":True})
    assert m["supervisory_escalation_required"] and m["human_decision_required"]


def test_release78_human_challenge_and_governance_boundaries():
    svc=RegulatoryExaminationReclosedInterventionSustainabilityService(None,"tenant-a")
    try: svc.human_challenge("ai",{"intervention_program_id":"p1","reviewer_role":"ai_agent","decision":"agree","rationale":"x","evidence_refs":[]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot perform mandatory human challenge")
    c=svc.human_challenge("audit",{"intervention_program_id":"p1","reviewer_role":"internal_auditor","decision":"challenge","rationale":"repeat failure","evidence_refs":["ev1"]})
    assert c["human_decision"] and not c["automated_decision"]
    try: svc.governance_action("exec",{"intervention_program_id":"p1","actor_role":"chief_risk_officer","action_type":"reopen_program","decision":"approve_investigation","rationale":"x","evidence_refs":[]})
    except PermissionError: pass
    else: raise AssertionError("Release 78 cannot reopen intervention programs")
    assert "multi-cycle recurrence" in reclosed_intervention_sustainability_contract()["traceability"]
