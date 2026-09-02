from app.domain.regulatory_post_closure_surveillance import POST_CLOSURE_AUTHORITY
from app.evaluation.regulatory_post_closure_surveillance import evaluate_recurrence_signal,evaluate_traceability

def test_release61_non_delegable_reopening_authority():
    assert POST_CLOSURE_AUTHORITY["ai_can_reopen_finding"] is False
    assert POST_CLOSURE_AUTHORITY["ai_can_close_reopened_finding"] is False
    assert POST_CLOSURE_AUTHORITY["ai_can_accept_residual_risk"] is False
    assert POST_CLOSURE_AUTHORITY["worker_can_collect_or_move_money"] is False

def test_release61_high_risk_signal_becomes_reopen_candidate():
    r=evaluate_recurrence_signal({"recurrence_score":.95,"sustainability_decay_score":.8,"control_regression_score":.9,"cross_entity_keys":["EU","US"]})
    assert r["reopen_candidate"] is True
    assert r["decision_authority"]=="human_only"

def test_release61_low_risk_signal_stays_below_reopen_threshold():
    r=evaluate_recurrence_signal({"recurrence_score":.2,"sustainability_decay_score":.1,"control_regression_score":.1})
    assert r["reopen_candidate"] is False

def test_release61_traceability_chain():
    r=evaluate_traceability({"closed_issue":1,"surveillance_signal":1,"recurrence_evidence":1,"human_reopening":1,"renewed_remediation":1,"revalidation":1})
    assert r["passed"] is True
