from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def test_reviewer_frontend_exposes_post_decision_workbench_and_human_controls():
    workbench=(ROOT/"frontend/components/review/claim-workbench.tsx").read_text()
    panel=(ROOT/"frontend/components/review/post-decision-operations.tsx").read_text()
    api=(ROOT/"frontend/lib/api.ts").read_text()
    assert 'label: "Post-decision"' in workbench
    assert "PostDecisionOperations" in workbench
    for marker in ("Human release notice","Governed final appeal resolution","Open governed appeal workbench","Immutable decision history","Correspondence provenance"):
        assert marker in panel
    for marker in ("releaseDecisionNotice","assignAppeal","reopenAppeal","appealResolution","postDecision"):
        assert marker in api


def test_portal_frontend_has_appeal_intake_without_internal_ai_reasoning():
    portal=(ROOT/"frontend/components/portal/claim-detail.tsx").read_text()
    api=(ROOT/"frontend/lib/api.ts").read_text()
    assert "Decision notices & appeals" in portal
    assert "Submit an appeal" in portal
    assert "linkAppealEvidence" in api
    assert "agent chain-of-thought" not in portal.lower()
    assert "fraud/waste" not in portal.lower()
