from app.domain.regulatory_examination_commitment_lifecycle import COMMITMENT_LIFECYCLE_AUTHORITY,commitment_lifecycle_contract
from app.evaluation.regulatory_examination_commitment_lifecycle import completion_readiness,reconciliation_flags,cross_examination_clusters
from app.services.regulatory_examination_commitment_lifecycle import RegulatoryExaminationCommitmentLifecycleService

def test_release68_non_delegable_authority():
    assert COMMITMENT_LIFECYCLE_AUTHORITY["ai_can_create_binding_commitment"] is False
    assert COMMITMENT_LIFECYCLE_AUTHORITY["ai_can_certify_completion"] is False
    assert COMMITMENT_LIFECYCLE_AUTHORITY["worker_can_certify_completion"] is False

def test_release68_completion_readiness_requires_evidence_and_effectiveness():
    c={"required_evidence_types":["deployment","control_test"]}
    r=completion_readiness(c,[{"status":"completed"}],[{"evidence_type":"deployment","status":"active"}],[{"result":"effective"}])
    assert r["ready"] is False and any("control_test" in b for b in r["blockers"])
    r2=completion_readiness(c,[{"status":"completed"}],[{"evidence_type":"deployment","status":"active"},{"evidence_type":"control_test","status":"active"}],[{"result":"effective"}])
    assert r2["ready"] is True and r2["automated_certification_allowed"] is False

def test_release68_written_verbal_reconciliation_and_cross_exam_correlation():
    c={"commitment_id":"c1","description":"Provide evidence","due_at":"2026-10-01T00:00:00Z"}
    f=reconciliation_flags(c,[{"commitment_id":"c1","description":"Provide evidence package","due_at":"2026-10-15T00:00:00Z","reference":"letter-1"}])
    assert {x["type"] for x in f}=={"description_mismatch","due_date_mismatch"}
    clusters=cross_examination_clusters([{"commitment_id":"a","examination_id":"e1","control_id":"ctrl","obligation_id":"o","normalized_theme":"data"},{"commitment_id":"b","examination_id":"e2","control_id":"ctrl","obligation_id":"o","normalized_theme":"data"}])
    assert clusters and clusters[0]["cross_examination"] is True

def test_release68_human_only_completion_certification_and_traceability():
    s=RegulatoryExaminationCommitmentLifecycleService(None,"tenant-a")
    payload={"reviewer_role":"analyst","decision":"certify_complete","rationale":"x","milestones":[{"status":"completed"}],"evidence":[],"validations":[{"result":"effective"}]}
    try:s.certify_completion("u","c",payload,{})
    except PermissionError: pass
    else: raise AssertionError("analyst cannot certify completion")
    ok={"reviewer_role":"regulatory_affairs","decision":"certify_complete","rationale":"validated","milestones":[{"status":"completed"}],"evidence":[],"validations":[{"result":"effective"}]}
    result=s.certify_completion("u","c",ok,{})
    assert result["human_certification"] is True and result["status"]=="completed"
    assert "human certification" in commitment_lifecycle_contract()["traceability"]
