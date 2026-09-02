from app.domain.regulatory_examination_response import EXAM_RESPONSE_AUTHORITY,examination_response_contract
from app.evaluation.regulatory_examination_response import evidence_refresh_status,detect_response_contradictions,reconciliation_status
from app.services.regulatory_examination_response import RegulatoryExaminationResponseService

def test_non_delegable_authority():
    assert EXAM_RESPONSE_AUTHORITY["ai_can_approve_submission"] is False
    assert EXAM_RESPONSE_AUTHORITY["ai_can_transmit_to_regulator"] is False
    assert EXAM_RESPONSE_AUTHORITY["ai_can_impersonate_regulator"] is False

def test_evidence_version_refresh_blocks_stale():
    r=evidence_refresh_status([{"evidence_id":"E1","version":"1"}],{"E1":"2"})
    assert r["fresh"] is False and r["stale_evidence_ids"]==["E1"]

def test_contradiction_detection_and_reconciliation():
    c=detect_response_contradictions("population=125; status=complete",[{"response_id":"R1","text":"population=100; status=complete"}])
    assert c and c[0]["field"]=="population"
    assert reconciliation_status({"human_approved":True},{"status":"acknowledged"},[])["reconciled"] is True
    assert reconciliation_status({"human_approved":True},{"status":"acknowledged"},[{"status":"open"}])["reconciled"] is False

def test_human_review_and_submission_boundary():
    s=RegulatoryExaminationResponseService(None,"tenant-a")
    try:s.review_revision("u","r","approve","analyst","ok")
    except PermissionError: pass
    else: raise AssertionError("analyst must not approve")
    approved=s.review_revision("u","r","approve","legal_reviewer","evidence checked")
    assert approved["human_decision"] is True
    sub=s.authorize_submission("u",{"revision_id":"r","authorized_channel":"portal","human_approved":True},"authorized_submitter")
    assert sub["automated_transmission_allowed"] is False
