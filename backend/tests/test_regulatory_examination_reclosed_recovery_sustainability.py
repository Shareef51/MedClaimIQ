from app.domain.regulatory_examination_reclosed_recovery_sustainability import RECLOSED_RECOVERY_SUSTAINABILITY_AUTHORITY,reclosed_recovery_sustainability_contract
from app.evaluation.regulatory_examination_reclosed_recovery_sustainability import recovery_decay_score,multi_cycle_recurrence,risk_rebound_correlation,enterprise_materiality
from app.services.regulatory_examination_reclosed_recovery_sustainability import RegulatoryExaminationReclosedRecoverySustainabilityService
def test_release86_non_delegable_authority():
    a=RECLOSED_RECOVERY_SUSTAINABILITY_AUTHORITY
    assert not a["ai_can_open_authoritative_investigation"] and not a["ai_can_reopen_or_reclose_program"] and not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_certify_recovery_effectiveness"] and not a["worker_can_reopen_program"]
def test_release86_decay_and_multi_cycle_recurrence():
    d=recovery_decay_score({"baseline_control_health_score":95,"current_control_health_score":70,"failed_observation_count":2,"stale_evidence_count":1,"sustainability_breach_count":1,"days_since_reclosure":60})
    assert d["recovery_decay_score"]>=25 and d["human_review_required"]
    r=multi_cycle_recurrence({"cycles":[{"status":"failed","root_cause_id":"rc1","control_id":"c1","entity_ids":["US","EU"]},{"status":"recurred","root_cause_id":"rc1","control_id":"c1","entity_ids":["APAC"]}]})
    assert r["multi_cycle_recurrence"] and r["systemic_recovery_failure_candidate"] and r["executive_internal_audit_challenge_required"]
def test_release86_risk_rebound_and_materiality():
    r=risk_rebound_correlation({"reclosure_risk_score":20,"risk_history":[{"score":20},{"score":55},{"score":60}]})
    assert r["risk_rebound_detected"] and r["peak_rebound"]==40
    m=enterprise_materiality({"failed_cycle_count":3,"affected_entity_count":4,"recovery_decay_score":70,"peak_rebound":40,"regulator_attention_escalation":True,"critical_service_impact":True})
    assert m["supervisory_escalation_tier"]>=3 and m["mandatory_executive_internal_audit_challenge"]
def test_release86_human_investigation_and_escalation_boundaries():
    svc=RegulatoryExaminationReclosedRecoverySustainabilityService(None,"tenant-a")
    try: svc.open_investigation("ai",{"actor_role":"ai_agent","recurrence_evidence_refs":["e1"],"materiality_score":80,"rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("AI cannot open authoritative investigation")
    inv=svc.open_investigation("aud1",{"actor_role":"internal_auditor","recurrence_evidence_refs":["e1"],"materiality_score":80,"rationale":"x"})
    assert inv["human_opened"]
    esc=svc.escalate("cro1",{"actor_role":"chief_risk_officer","investigation_version_id":inv["supervisory_investigation_version_id"],"escalation_tier":4,"decision":"escalate","rationale":"repeat failure","evidence_refs":["e2"]})
    assert esc["human_decision"] and not esc["automated_program_reopening"]
    assert "human investigation" in reclosed_recovery_sustainability_contract()["traceability"]
