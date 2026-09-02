from app.domain.regulatory_examination_readiness import EXAMINATION_READINESS_AUTHORITY, examination_readiness_contract
from app.evaluation.regulatory_examination_readiness import readiness_score, detect_evidence_conflicts, validate_cited_draft
from app.services.regulatory_examination_readiness import RegulatoryExaminationReadinessService


def test_release65_non_delegable_submission_authority():
    a = EXAMINATION_READINESS_AUTHORITY
    assert a["ai_can_approve_regulator_response"] is False
    assert a["ai_can_transmit_to_regulator"] is False
    assert a["worker_can_approve_submission_package"] is False
    assert a["worker_can_collect_or_move_money"] is False
    assert "regulator request" in examination_readiness_contract()["traceability"]


def test_release65_readiness_gate_requires_all_material_controls():
    complete = {"request_coverage":1,"evidence_completeness":1,"citation_validation":1,"conflict_resolution":1,"privileged_segregation":1,"owner_assignment":1,"deadline_health":1}
    assert readiness_score(complete)["score"] == 100
    assert readiness_score(complete)["ready_for_human_submission_review"] is True
    incomplete = {**complete, "citation_validation":0.5}
    assert readiness_score(incomplete)["ready_for_human_submission_review"] is False


def test_release65_evidence_conflict_and_privilege_safe_citation():
    ev = [
      {"evidence_id":"E1","citation_anchor":"A","content_hash":"h1","approved_for_exam_use":True,"evidence_class":"standard"},
      {"evidence_id":"E2","citation_anchor":"A","content_hash":"h2","approved_for_exam_use":True,"evidence_class":"legal_privileged"},
    ]
    assert detect_evidence_conflicts(ev)["human_resolution_required"] is True
    v = validate_cited_draft({"citation_ids":["E2"]}, ev)
    assert v["passed"] is False and v["human_approval_required"] is True


def test_release65_package_requires_human_approved_response_and_never_auto_transmits():
    s = RegulatoryExaminationReadinessService(None, "T1")
    s.create_scope("U1", {"examination_id":"EX1","regulator":"R1","legal_entity_ids":["LE1"],"scope_topics":["AML"],"start_at":"2026-08-22T00:00:00Z","target_end_at":None,"owner_id":"U1"})
    req = s.create_regulator_request("U1", {"examination_id":"EX1","external_request_ref":"REQ-1","request_text":"Provide control evidence","due_at":"2026-09-01T00:00:00Z","owner_id":"U1","priority":"high","requested_artifact_types":["control_test"]})
    s.map_evidence("U1", {"request_id":req["request_id"],"evidence_id":"E1","evidence_class":"standard","source_system":"GRC","version_id":"v1","content_hash":"a"*64,"citation_anchor":"CTRL-1","approved_for_exam_use":True})
    draft = s.create_draft("AI_ASSIST", {"request_id":req["request_id"],"answer":"Control tested.","citation_ids":["E1"],"generated_by":"ai_assisted"})
    try:
        s.build_package("U1", {"examination_id":"EX1","request_ids":[req["request_id"]],"package_name":"P1"})
        assert False, "unapproved draft must block package"
    except PermissionError:
        pass
    approved = s.decide_draft("HUMAN1", req["request_id"], "approve", "evidence verified", draft["version"])
    pkg = s.build_package("HUMAN1", {"examination_id":"EX1","request_ids":[req["request_id"]],"package_name":"P1"})
    assert approved["status"] == "human_approved"
    assert pkg["transmit_authority"] is False and pkg["immutable"] is True
