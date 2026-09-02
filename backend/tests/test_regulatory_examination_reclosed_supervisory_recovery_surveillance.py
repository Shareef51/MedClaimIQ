from app.domain.regulatory_examination_reclosed_supervisory_recovery_surveillance import RECLOSED_SUPERVISORY_RECOVERY_SURVEILLANCE_AUTHORITY, reclosed_supervisory_recovery_surveillance_contract
from app.evaluation.regulatory_examination_reclosed_supervisory_recovery_surveillance import multi_cycle_supervisory_recovery_decay, control_retransformation_regression, systemic_risk_rebound, cross_entity_recurrence, prior_supervisory_reclosure_comparison, enterprise_materiality, enterprise_reopening_readiness
from app.services.regulatory_examination_reclosed_supervisory_recovery_surveillance import RegulatoryExaminationReclosedSupervisoryRecoverySurveillanceService


def test_release94_non_delegable_authority_and_release93_provenance():
    a=RECLOSED_SUPERVISORY_RECOVERY_SURVEILLANCE_AUTHORITY
    assert a["release93_supervisory_reclosure_reference_required"] and a["independent_reassessment_required"] and a["human_reopening_decision_required"]
    assert not a["ai_can_open_authoritative_investigation"] and not a["ai_can_reopen_program"] and not a["ai_can_accept_residual_systemic_risk"] and not a["worker_can_reopen_program"]
    svc=RegulatoryExaminationReclosedSupervisoryRecoverySurveillanceService(None,"tenant-a")
    try: svc.decay({"recovery_program_id":"rp1"})
    except ValueError: pass
    else: raise AssertionError("Release 93 reclosure provenance must be mandatory")


def test_release94_multi_cycle_decay_regression_rebound_and_recurrence():
    d=multi_cycle_supervisory_recovery_decay({"release93_reclosure_control_health_score":95,"current_control_health_score":67,"control_retransformation_regressions":2,"prior_supervisory_recovery_failure_cycles":3,"sustainability_breach_count":1})
    assert d["multi_cycle_supervisory_recovery_decay_score"] >= 50 and d["repeated_supervisory_recovery_failure_candidate"] and d["human_investigation_required"]
    g=control_retransformation_regression({"controls":[{"control_id":"c1","release93_reclosure_status":"effective","current_status":"failed","severity":"critical","evidence_refs":["e1"]},{"control_id":"c2","current_status":"effective","evidence_refs":["e2"]}]})
    assert g["material_control_regression_candidate"] and g["regressed_control_ids"] == ["c1"]
    r=systemic_risk_rebound({"release93_reclosure_systemic_risk_score":20,"current_systemic_risk_score":38,"peak_post_reclosure_systemic_risk_score":42})
    assert r["material_systemic_risk_rebound_candidate"] and r["systemic_risk_rebound_percent"] == 90.0
    x=cross_entity_recurrence({"expected_entity_count":4,"entities":[{"entity_id":"US","status":"failed","severity":"critical","evidence_refs":["e1"]},{"entity_id":"EU","post_reclosure_failure_count":2,"evidence_refs":["e2"]}]})
    assert x["cross_entity_recurrence_propagation"] and x["cross_entity_recurrence_percent"] == 50.0


def test_release94_prior_comparison_materiality_and_reopening_readiness():
    c=prior_supervisory_reclosure_comparison({"prior":{"control_health_score":95,"systemic_risk_score":20,"control_ids":["c1"],"root_cause_ids":["r1"],"supervisory_recovery_recertification_version_id":"rc1","supervisory_sustainability_reclosure_version_id":"sr1"},"current":{"control_health_score":70,"systemic_risk_score":41,"control_ids":["c1"],"root_cause_ids":["r1"]}})
    assert c["prior_supervisory_reclosure_degradation_candidate"] and c["repeated_root_cause_ids"] == ["r1"]
    m=enterprise_materiality({"multi_cycle_supervisory_recovery_decay_score":80,"control_retransformation_regression_percent":50,"cross_entity_recurrence_percent":50,"systemic_risk_rebound_percent":90,"prior_supervisory_recovery_failure_cycles":3,"adverse_regulator_followup_count":1})
    assert m["enterprise_materiality_tier"] in {"enterprise_high","enterprise_critical"} and m["executive_internal_audit_escalation_required"]
    ready=enterprise_reopening_readiness({"release93_supervisory_reclosure_reference_validated":True,"material_multi_cycle_decay_confirmed":True,"human_investigation_complete":True,"independent_reassessment_complete":True,"prior_executive_recertification_reclosure_compared":True,"cross_entity_recurrence_scope_validated":True,"new_examination_finding_links_human_validated":True,"regulator_followups_human_interpreted":True,"enterprise_materiality_human_validated":True,"executive_review_complete":True,"internal_audit_challenge_complete":True,"renewed_recovery_governance_candidate_prepared":True})
    assert ready["ready_for_human_enterprise_reopening"] and ready["enterprise_reopening_readiness_score"] == 100.0


def test_release94_human_only_investigation_reassessment_challenge_and_reopening():
    svc=RegulatoryExaminationReclosedSupervisoryRecoverySurveillanceService(None,"tenant-a")
    try: svc.create_investigation("ai",{"actor_role":"ai_agent","recovery_program_id":"rp1","release93_supervisory_sustainability_reclosure_version_id":"sr1","summary":"x","surveillance_version_refs":["sv1"],"evidence_refs":["e1"]})
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative supervisory recovery investigation")
    reassess=svc.independent_reassess("ia1",{"actor_role":"internal_auditor","recovery_program_id":"rp1","result":"confirmed_decay","conclusion":"multi-cycle degradation confirmed","investigation_version_id":"i1","evidence_refs":["e1"]})
    assert reassess["human_reassessment"] and not reassess["automated_reassessment"]
    try: svc.decide_reopening("ai",{"actor_role":"ai_agent","decision":"reopen","recovery_program_id":"rp1","release93_supervisory_sustainability_reclosure_version_id":"sr1","investigation_version_id":"i1","independent_reassessment_version_id":"ir1","supervisory_challenge_version_id":"sc1","readiness":{}})
    except PermissionError: pass
    else: raise AssertionError("AI cannot reopen supervisory recovery program")
    assert "human enterprise reopening" in reclosed_supervisory_recovery_surveillance_contract()["traceability"]
