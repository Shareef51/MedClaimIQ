from app.domain.regulatory_examination_interaction import INTERACTION_AUTHORITY,examination_interaction_contract
from app.evaluation.regulatory_examination_interaction import detect_commitment_candidates,separate_positions,contradiction_flags
from app.services.regulatory_examination_interaction import RegulatoryExaminationInteractionService

def test_non_delegable_commitment_authority():
    assert INTERACTION_AUTHORITY["ai_can_create_binding_commitment"] is False
    assert INTERACTION_AUTHORITY["ai_can_represent_regulator_intent"] is False
    assert INTERACTION_AUTHORITY["worker_can_confirm_commitment"] is False

def test_position_separation_and_candidate_detection():
    items=[{"statement_id":"1","text":"We will provide by 2026-09-15","classification":"enterprise_statement"},{"statement_id":"2","text":"Examiner requested evidence","classification":"documented_regulator_position"},{"statement_id":"3","text":"Team believes scope is narrow","classification":"enterprise_interpretation"}]
    assert len(detect_commitment_candidates(items))==1
    p=separate_positions(items); assert len(p["documented_regulator_positions"])==1 and len(p["enterprise_interpretations"])==1

def test_human_only_commitment_confirmation():
    s=RegulatoryExaminationInteractionService(None,"tenant-a")
    c=s.create_commitment_candidate("u",{"meeting_id":"m","statement_id":"s","description":"deliver evidence"})
    assert c["binding"] is False
    try:s.decide_commitment("u",c["commitment_id"],{"decision":"confirm","reviewer_role":"analyst","rationale":"x"})
    except PermissionError: pass
    else: raise AssertionError("analyst must not confirm regulatory commitment")
    d=s.decide_commitment("u",c["commitment_id"],{"decision":"confirm","reviewer_role":"regulatory_affairs","rationale":"validated","owner_user_id":"o","due_at":"2026-09-15T00:00:00Z"})
    assert d["binding"] is True and d["human_decision"] is True

def test_contradiction_and_traceability_contract():
    f=contradiction_flags([{"statement_id":"s","text":"Status complete"}],[{"text":"status not complete"}])
    assert f and f[0]["reason"]=="completion_status_conflict"
    assert "human validation" in examination_interaction_contract()["traceability"]
