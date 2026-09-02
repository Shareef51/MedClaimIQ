from app.domain.regulatory_examination_reopened_commitment_reclosure import REOPENED_COMMITMENT_RECLOSURE_AUTHORITY, reopened_commitment_reclosure_contract
from app.evaluation.regulatory_examination_reopened_commitment_reclosure import compare_recurrence_root_causes, reclosure_readiness, second_recurrence_assessment, sustainability_reset_window
from app.services.regulatory_examination_reopened_commitment_reclosure import RegulatoryExaminationReopenedCommitmentReclosureService

def test_release71_non_delegable_recertification_and_reclosure_authority():
    assert REOPENED_COMMITMENT_RECLOSURE_AUTHORITY["ai_can_recertify_commitment"] is False
    assert REOPENED_COMMITMENT_RECLOSURE_AUTHORITY["ai_can_reclose_commitment"] is False
    assert REOPENED_COMMITMENT_RECLOSURE_AUTHORITY["worker_can_reclose_commitment"] is False

def test_release71_root_cause_and_second_recurrence_governance():
    c=compare_recurrence_root_causes({"primary_root_cause_id":"r1","root_cause_ids":["r1"],"control_ids":["c1"]},{"primary_root_cause_id":"r1","root_cause_ids":["r1","r2"],"control_ids":["c1"]})
    assert c["recurrence_pattern_confirmed"] is True and c["human_review_required"] is True
    r=second_recurrence_assessment([{"event_type":"recurrence"},{"event_type":"control_failure"}])
    assert r["second_recurrence"] is True and r["executive_escalation_required"] is True

def test_release71_reclosure_readiness_and_sustainability_reset():
    ready=reclosure_readiness({"renewed_plan_approved":True,"all_milestones_complete":True,"cross_entity_propagation_complete":True,"regulator_follow_up_reconciled":True,"independent_retest_passed":True,"independent_revalidation_complete":True,"evidence_sufficient":True,"sustainability_reset_ready":True,"second_recurrence_detected":False})
    assert ready["score"]==100 and ready["ready"] is True
    blocked=reclosure_readiness({"second_recurrence_detected":True})
    assert blocked["ready"] is False and "second_recurrence_absent" in blocked["blockers"]
    assert sustainability_reset_window({"severity":"high","recurrence_count":2})["minimum_monitoring_days"]==270

def test_release71_human_only_recertification_reclosure_and_traceability():
    s=RegulatoryExaminationReopenedCommitmentReclosureService(None,"tenant-a")
    readiness={"ready":True,"score":100}
    try:s.recertify("u","c",{"reviewer_role":"analyst","decision":"recertify","rationale":"x","readiness":readiness})
    except PermissionError:pass
    else:raise AssertionError("analyst cannot recertify")
    rc=s.recertify("u","c",{"reviewer_role":"executive_certifier","decision":"recertify","rationale":"validated","readiness":readiness,"evidence_refs":["e1"]})
    assert rc["human_decision"] is True and rc["recertified"] is True
    closed=s.decide_reclosure("u","c",{"reviewer_role":"regulatory_affairs","decision":"reclose","rationale":"sustained","recertification_id":rc["recertification_id"],"sustainability_window":{"reset_required":True,"minimum_monitoring_days":90}})
    assert closed["reclosed"] is True and len(closed["version_hash"])==64
    assert "human recertification" in reopened_commitment_reclosure_contract()["traceability"]
