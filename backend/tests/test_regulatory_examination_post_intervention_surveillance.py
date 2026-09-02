from app.domain.regulatory_examination_post_intervention_surveillance import POST_INTERVENTION_SURVEILLANCE_AUTHORITY, post_intervention_surveillance_contract
from app.evaluation.regulatory_examination_post_intervention_surveillance import systemic_recurrence_signal, examination_match, cross_entity_propagation, reopening_readiness
from app.services.regulatory_examination_post_intervention_surveillance import RegulatoryExaminationPostInterventionSurveillanceService

def test_release76_non_delegable_authority():
    a=POST_INTERVENTION_SURVEILLANCE_AUTHORITY
    assert a["ai_can_reopen_intervention_program"] is False
    assert a["worker_can_reopen_intervention_program"] is False
    assert a["ai_can_accept_residual_systemic_risk"] is False
    assert a["ai_can_certify_effectiveness"] is False

def test_release76_recurrence_and_exam_matching():
    s=systemic_recurrence_signal({"closure_systemic_risk_score":10,"current_systemic_risk_score":30,"systemic_risk_rebound_threshold":15})
    assert s["reopen_candidate"] and "systemic_risk_rebound" in s["reasons"] and s["automated_reopening_allowed"] is False
    m=examination_match({"obligation_overlap":.9,"control_overlap":.8,"root_cause_similarity":.8,"entity_overlap":.5})
    assert m["likely_related"] and m["authoritative_regulatory_conclusion"] is False

def test_release76_cross_entity_and_readiness_gates():
    p=cross_entity_propagation({"affected_entity_ids":["US","EU"],"program_entity_ids":["US","EU","APAC"]})
    assert p["cross_entity_systemic_candidate"]
    ready=reopening_readiness({"investigation_complete":True,"independent_reassessment_complete":True,"executive_review_complete":True,"internal_audit_review_complete":True,"renewed_remediation_candidate_defined":True})
    assert ready["reopening_readiness_score"]==100 and ready["ready_for_human_reopening_decision"]

def test_release76_human_only_reopening():
    svc=RegulatoryExaminationPostInterventionSurveillanceService(None,"tenant-a")
    inv=svc.open_investigation("analyst",{"intervention_program_id":"p1","finding_ids":["f1"],"affected_entity_ids":["US","EU"],"program_entity_ids":["US","EU"],"root_cause_comparison":{},"prior_closure_version_id":"c1","prior_residual_risk_acceptance_version_id":"r1","regulator_followup_refs":[],"renewed_action_plan_refs":["plan2"],"rationale":"recurrence"})
    reass=svc.independent_reassessment("audit",{"intervention_program_id":"p1","investigation_version_id":inv["recurrence_investigation_version_id"],"reviewer_role":"internal_auditor","effectiveness_reconfirmed":False,"residual_systemic_risk_score":45,"evidence_refs":["ev2"],"rationale":"control regression"})
    try: svc.reopening_decision("ai",{"intervention_program_id":"p1","reviewer_role":"ai_agent","decision":"reopen","reopening_readiness_score":100,"investigation_version_id":inv["recurrence_investigation_version_id"],"independent_reassessment_version_id":reass["independent_reassessment_version_id"],"rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot reopen intervention program")
    d=svc.reopening_decision("cro",{"intervention_program_id":"p1","reviewer_role":"chief_risk_officer","decision":"reopen","reopening_readiness_score":100,"investigation_version_id":inv["recurrence_investigation_version_id"],"independent_reassessment_version_id":reass["independent_reassessment_version_id"],"rationale":"all gates complete","evidence_refs":["ev2"]})
    assert d["human_decision"] and d["automated_reopening"] is False
    assert "program reopening" in post_intervention_surveillance_contract()["traceability"]
