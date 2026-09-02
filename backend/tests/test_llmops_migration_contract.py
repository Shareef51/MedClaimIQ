from pathlib import Path
M=(Path(__file__).resolve().parents[1]/"alembic/versions/0020_llmops_observability.py").read_text()
def test_llmops_tables_and_rls():
    for t in ("ai_usage_ledger","ai_slo_events"): assert t in M
    assert "FORCE ROW LEVEL SECURITY" in M
def test_llmops_history_is_immutable():
    assert "medclaimiq_reject_immutable_change" in M
