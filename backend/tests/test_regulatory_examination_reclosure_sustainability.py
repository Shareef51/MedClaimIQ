from app.domain.regulatory_examination_reclosure_sustainability import RECLOSURE_SUSTAINABILITY_AUTHORITY,reclosure_sustainability_contract
from app.evaluation.regulatory_examination_reclosure_sustainability import sustainability_decay,repeat_recurrence_score,escalation_tier,compare_reclosures
from app.services.regulatory_examination_reclosure_sustainability import RegulatoryExaminationReclosureSustainabilityService

def test_release72_non_delegable_authority():
    assert RECLOSURE_SUSTAINABILITY_AUTHORITY["ai_can_reopen_commitment"] is False
    assert RECLOSURE_SUSTAINABILITY_AUTHORITY["worker_can_reopen_commitment"] is False
    assert RECLOSURE_SUSTAINABILITY_AUTHORITY["worker_can_certify_effectiveness"] is False

def test_release72_decay_repeat_recurrence_and_systemic_pattern():
    d=sustainability_decay({"baseline_control_health":100,"current_control_health":55,"days_since_reclosure":300,"stale_evidence_count":2,"failed_observation_count":1})
    assert d["decay_score"]>=50 and d["human_review_required"] is True
    r=repeat_recurrence_score([{"event_type":"recurrence"},{"event_type":"control_failure"},{"event_type":"reclosure_failure"}],3)
    assert r["third_occurrence"] is True and r["systemic_pattern_candidate"] is True
    assert r["mandatory_executive_review"] and r["mandatory_internal_audit_review"]

def test_release72_escalation_and_prior_reclosure_comparison():
    e=escalation_tier({"recurrence_count":3,"decay_score":60,"affected_entity_count":4,"regulator_follow_up_overdue":True})
    assert e["tier"]>=3 and e["executive_review_required"]
    c=compare_reclosures({"control_health":90,"root_cause_id":"r1","control_id":"c1"},{"control_health":60,"root_cause_id":"r1","control_id":"c1"})
    assert c["control_health_delta"]==-30 and c["same_root_cause"]

def test_release72_human_investigation_and_governance_action_traceability():
    s=RegulatoryExaminationReclosureSustainabilityService(None,"tenant-a")
    esc=s.create_escalation("u",{"recurrence_count":3,"decay_score":70,"affected_entity_count":3,"regulator_follow_up_overdue":True})
    try:s.open_investigation("u",{"commitment_id":"c","escalation_version_id":esc["escalation_version_id"],"reviewer_role":"analyst","rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("analyst cannot open governed investigation")
    inv=s.open_investigation("u",{"commitment_id":"c","escalation_version_id":esc["escalation_version_id"],"reviewer_role":"internal_auditor","rationale":"repeat recurrence","evidence_refs":["e1"]})
    action=s.create_governance_action("u",{"commitment_id":"c","investigation_id":inv["investigation_id"],"reviewer_role":"executive_certifier","action_type":"executive_escalation","rationale":"third occurrence","evidence_refs":["e1"]})
    assert inv["human_decision"] and action["human_decision"] and len(action["version_hash"])==64
    assert "human investigation" in reclosure_sustainability_contract()["traceability"]
