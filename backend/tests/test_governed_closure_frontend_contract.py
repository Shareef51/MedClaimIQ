from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def test_reviewer_ui_uses_governed_packet_workflow():
    component=(ROOT/'frontend/components/review/governed-decision-panel.tsx').read_text()
    workbench=(ROOT/'frontend/components/review/claim-workbench.tsx').read_text()
    api=(ROOT/'frontend/lib/api.ts').read_text()
    for marker in ['Human authority boundary','Reviewer decision packet','Evidence completeness & blockers','Dual-control second review','Governed closure','Immutable adjudication audit chain']:
        assert marker in component
    assert '<GovernedDecisionPanel' in workbench
    assert 'saveDecisionPacket' in api and 'validateDecisionPacket' in api and 'secondReviewDecisionPacket' in api and 'closeDecisionPacket' in api


def test_old_browser_direct_decision_route_is_retired():
    api=(ROOT/'backend/app/api/v1/review_workbench.py').read_text()
    assert 'Direct human-decision endpoint is retired for adjudicative actions' in api


def test_ui_states_ai_is_advisory_and_no_financial_execution_occurs():
    component=(ROOT/'frontend/components/review/governed-decision-panel.tsx').read_text()
    assert 'They cannot approve, deny, partially approve, financially execute, or close this claim.' in component
    assert 'does not execute payment or any automated financial transaction' in component
