from app.domain.regulatory_knowledge_governance import KNOWLEDGE_GOVERNANCE_AUTHORITY, knowledge_governance_contract
from app.evaluation.regulatory_knowledge_governance import temporal_relevance, detect_knowledge_conflict, readiness_score, evaluate_cited_answer


def test_release64_non_delegable_knowledge_authority():
    a = KNOWLEDGE_GOVERNANCE_AUTHORITY
    assert a["ai_can_publish_authoritative_knowledge"] is False
    assert a["ai_can_classify_authoritative_regulatory_interpretation"] is False
    assert a["ai_can_approve_policy_or_control_changes"] is False
    assert a["worker_can_collect_or_move_money"] is False


def test_release64_temporal_graph_rag_respects_versions():
    r = temporal_relevance({"effective_at":"2026-01-01T00:00:00Z","expires_at":"2026-09-01T00:00:00Z","status":"authoritative","version_id":"v3"}, "2026-08-22T00:00:00Z")
    assert r == {"applicable": True, "as_of": "2026-08-22T00:00:00Z", "version_id": "v3"}


def test_release64_conflicts_require_human_resolution():
    r = detect_knowledge_conflict([
      {"status":"authoritative","normalized_position":"retain 7 years","evidence_refs":["E1"]},
      {"status":"approved_internal","normalized_position":"retain 10 years","evidence_refs":["E2"]},
    ])
    assert r["conflict_detected"] is True and r["human_resolution_required"] is True


def test_release64_readiness_and_citation_traceability():
    r = readiness_score({"authoritative_coverage":1,"evidence_freshness":1,"control_lineage_coverage":1,"open_conflict_resolution":1,"historical_finding_coverage":1})
    assert r["score"] == 100 and r["ready"] is True
    q = evaluate_cited_answer({"material_claims":[{"citation_ids":["E1"]}],"citations":[{"knowledge_class":"authoritative"}]})
    assert q["passed"] is True and q["decision_authority"] == "human_only"
    assert "knowledge graph" in knowledge_governance_contract()["traceability"]
