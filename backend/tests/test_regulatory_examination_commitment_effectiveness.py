from app.domain.regulatory_examination_commitment_effectiveness import COMMITMENT_EFFECTIVENESS_AUTHORITY,commitment_effectiveness_contract
from app.evaluation.regulatory_examination_commitment_effectiveness import closure_readiness,sustainability_state,recurrence_match
from app.services.regulatory_examination_commitment_effectiveness import RegulatoryExaminationCommitmentEffectivenessService

def test_release69_non_delegable_authority():
    assert COMMITMENT_EFFECTIVENESS_AUTHORITY["ai_can_certify_commitment_completion"] is False
    assert COMMITMENT_EFFECTIVENESS_AUTHORITY["ai_can_close_regulatory_obligation"] is False
    assert COMMITMENT_EFFECTIVENESS_AUTHORITY["worker_can_certify_closure"] is False

def test_release69_closure_readiness_blocks_dependencies_and_followups():
    base={"required_evidence_types":["control_test"]}; ev=[{"evidence_type":"control_test","sha256":"a"*64,"status":"active"}]; val=[{"independent":True,"result":"effective"}]
    r=closure_readiness(base,[{"status":"completed"}],ev,val,[{"status":"blocked"}],[{"status":"open"}],[{"implemented":True}])
    assert r["ready"] is False and "dependencies_unresolved" in r["blockers"] and "regulator_follow_up_unreconciled" in r["blockers"]
    r2=closure_readiness(base,[{"status":"completed"}],ev,val,[{"status":"completed"}],[{"status":"acknowledged"}],[{"implemented":True}])
    assert r2["ready"] is True and r2["automated_closure_allowed"] is False

def test_release69_sustainability_and_recurrence_detection():
    assert sustainability_state([{"days_since_closure":40,"health_score":93,"control_effective":True}],30)["state"]=="stable"
    failed=sustainability_state([{"days_since_closure":12,"control_effective":False}],30)
    assert failed["reopen_candidate"] is True
    matches=recurrence_match({"control_id":"c","obligation_id":"o","normalized_theme":"data"},[{"signal_id":"s","control_id":"c","obligation_id":"o"}])
    assert matches and matches[0]["candidate"] is True

def test_release69_human_only_closure_and_reopen_traceability():
    s=RegulatoryExaminationCommitmentEffectivenessService(None,"tenant-a")
    payload={"reviewer_role":"analyst","decision":"certify_closed","rationale":"x","commitment":{},"milestones":[],"evidence":[],"validations":[],"dependencies":[],"follow_ups":[],"entity_checks":[]}
    try:s.certify_closure("u","c",payload)
    except PermissionError:pass
    else:raise AssertionError("analyst cannot certify closure")
    good={"reviewer_role":"regulatory_affairs","decision":"certify_closed","rationale":"validated","commitment":{},"milestones":[{"status":"completed"}],"evidence":[],"validations":[{"independent":True,"result":"effective"}],"dependencies":[],"follow_ups":[],"entity_checks":[]}
    result=s.certify_closure("u","c",good)
    assert result["human_certification"] is True and result["status"]=="certified_closed"
    assert "sustainability surveillance" in commitment_effectiveness_contract()["traceability"]
    decision=s.decide_reopen("u","c",{"reviewer_role":"internal_auditor","decision":"reopen","rationale":"recurrence"})
    assert decision["human_decision"] is True and decision["reopened"] is True
