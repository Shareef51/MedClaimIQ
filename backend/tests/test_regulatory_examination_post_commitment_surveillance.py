from app.domain.regulatory_examination_post_commitment_surveillance import POST_COMMITMENT_SURVEILLANCE_AUTHORITY, post_commitment_surveillance_contract
from app.evaluation.regulatory_examination_post_commitment_surveillance import sustainability_decay, match_new_examination, cross_entity_recurrence, compare_prior_certification
from app.services.regulatory_examination_post_commitment_surveillance import RegulatoryExaminationPostCommitmentSurveillanceService


def test_release70_non_delegable_reopening_authority():
    assert POST_COMMITMENT_SURVEILLANCE_AUTHORITY["ai_can_reopen_commitment"] is False
    assert POST_COMMITMENT_SURVEILLANCE_AUTHORITY["worker_can_reopen_commitment"] is False
    assert POST_COMMITMENT_SURVEILLANCE_AUTHORITY["worker_can_certify_effectiveness"] is False


def test_release70_decay_and_new_exam_recurrence_detection():
    stable=sustainability_decay([{"days_since_closure":30,"health_score":95},{"days_since_closure":90,"health_score":93}])
    assert stable["state"]=="stable" and stable["reopen_candidate"] is False
    degraded=sustainability_decay([{"days_since_closure":30,"health_score":96},{"days_since_closure":120,"health_score":72}])
    assert degraded["reopen_candidate"] is True
    matches=match_new_examination({"control_id":"c","obligation_id":"o","normalized_theme":"data"},[{"finding_id":"f","control_id":"c","obligation_id":"o"}])
    assert matches and matches[0]["candidate"] is True


def test_release70_cross_entity_and_prior_certification_comparison():
    result=cross_entity_recurrence([{"entity_id":"US","control_id":"c","recurrence_detected":True},{"entity_id":"EU","control_id":"c","control_effective":False}],2)
    assert result["candidate"] is True and len(result["affected_entities"])==2
    comparison=compare_prior_certification({"effectiveness_score":95,"control_effective":True,"scope_entities":["US","EU"]},{"effectiveness_score":70,"control_effective":False,"scope_entities":["US"]})
    assert comparison["material_change"] is True and comparison["contradictions"]


def test_release70_human_only_reopen_and_traceability():
    s=RegulatoryExaminationPostCommitmentSurveillanceService(None,"tenant-a")
    try:s.decide_reopen("u","c",{"investigation_id":"i","reviewer_role":"analyst","decision":"reopen","rationale":"x"})
    except PermissionError:pass
    else:raise AssertionError("analyst cannot reopen commitment")
    d=s.decide_reopen("u","c",{"investigation_id":"i","reviewer_role":"internal_auditor","decision":"reopen","rationale":"recurrence","evidence_refs":["e1"]})
    assert d["human_decision"] is True and d["reopened"] is True and len(d["version_hash"])==64
    assert "renewed corrective action" in post_commitment_surveillance_contract()["traceability"]
