from app.domain.regulatory_examination_reclosed_reauthorized_recovery_surveillance import RECLOSED_REAUTHORIZED_RECOVERY_SURVEILLANCE_AUTHORITY,reclosed_reauthorized_recovery_surveillance_contract
from app.evaluation.regulatory_examination_reclosed_reauthorized_recovery_surveillance import repeated_recovery_decay,systemic_risk_rebound,cross_entity_recurrence,prior_reclosure_comparison,examination_finding_correlation,enterprise_reopening_readiness
from app.services.regulatory_examination_reclosed_reauthorized_recovery_surveillance import RegulatoryExaminationReclosedReauthorizedRecoverySurveillanceService

def test_release90_non_delegable_authority():
    a=RECLOSED_REAUTHORIZED_RECOVERY_SURVEILLANCE_AUTHORITY
    assert not a["ai_can_reopen_program"] and not a["ai_can_reclose_program"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"]
    assert not a["worker_can_reopen_program"] and a["independent_reassessment_required"] and a["human_reopening_decision_required"]

def test_release90_decay_rebound_recurrence_and_prior_comparison():
    d=repeated_recovery_decay({"reclosure_control_health_score":94,"current_control_health_score":68,"repeated_failure_control_regressions":2,"sustainability_breach_count":1,"prior_recovery_failure_cycles":2})
    assert d["repeated_recovery_decay_score"]>=50 and d["human_investigation_required"]
    r=systemic_risk_rebound({"reclosure_systemic_risk_score":20,"current_systemic_risk_score":38,"peak_post_reclosure_risk_score":45})
    assert r["material_rebound_candidate"] and r["systemic_risk_rebound_percent"]==90.0
    x=cross_entity_recurrence({"expected_entity_count":4,"entities":[{"entity_id":"US","status":"failed","severity":"critical","evidence_refs":["e1"]},{"entity_id":"EU","failure_count":2,"severity":"high","evidence_refs":["e2"]}]})
    assert x["cross_entity_recurrence_propagation"] and x["recurrence_propagation_percent"]==50.0
    c=prior_reclosure_comparison({"prior":{"control_health_score":94,"systemic_risk_score":20,"control_ids":["c1"],"root_cause_ids":["r1"]},"current":{"control_health_score":70,"systemic_risk_score":39,"control_ids":["c1"],"root_cause_ids":["r1"]}})
    assert c["prior_reclosure_degradation_candidate"] and c["repeated_control_ids"]==["c1"]

def test_release90_examination_correlation_and_reopening_readiness():
    m=examination_finding_correlation({"items":[{"examination_id":"ex1","finding_id":"f1","root_cause_similarity":.9,"control_overlap":.8,"entity_overlap":.7,"regulatory_obligation_overlap":.9}]})
    assert m["new_examination_finding_correlation"] and not m["regulator_intent_inferred"]
    ready=enterprise_reopening_readiness({"material_decay_confirmed":True,"human_investigation_complete":True,"independent_reassessment_complete":True,"prior_recertification_reclosure_compared":True,"cross_entity_scope_validated":True,"new_examination_finding_links_human_validated":True,"regulator_followups_human_interpreted":True,"executive_review_complete":True,"internal_audit_challenge_complete":True,"renewed_recovery_governance_candidate_prepared":True})
    assert ready["ready_for_human_enterprise_reopening"] and ready["enterprise_reopening_readiness_score"]==100.0

def test_release90_human_only_investigation_reassessment_and_reopening():
    svc=RegulatoryExaminationReclosedReauthorizedRecoverySurveillanceService(None,"tenant-a")
    try: svc.create_investigation("ai",{"actor_role":"ai_agent","recovery_program_id":"rp1","summary":"x","surveillance_version_refs":["sv1"],"evidence_refs":["e1"]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative investigation")
    try: svc.decide_reopening("ai",{"actor_role":"ai_agent","decision":"reopen","recovery_program_id":"rp1","investigation_version_id":"i1","independent_reassessment_version_id":"ir1","supervisory_challenge_version_id":"sc1","readiness":{}})
    except PermissionError: pass
    else: raise AssertionError("AI cannot reopen enterprise recovery program")
    reassess=svc.independent_reassess("ia1",{"actor_role":"internal_auditor","recovery_program_id":"rp1","result":"confirmed_decay","conclusion":"repeated degradation confirmed","evidence_refs":["e1"],"investigation_version_id":"i1"})
    assert reassess["human_reassessment"] and not reassess["automated_reassessment"]
    assert "human reopening" in reclosed_reauthorized_recovery_surveillance_contract()["traceability"]
