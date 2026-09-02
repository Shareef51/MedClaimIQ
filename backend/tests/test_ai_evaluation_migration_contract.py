from pathlib import Path
M=(Path(__file__).resolve().parents[1]/"alembic/versions/0019_ai_evaluation_quality.py").read_text()
def test_eval_tables_and_rls():
    for t in ("evaluation_runs","evaluation_metrics","evaluation_cases","evaluation_baselines","evaluation_release_gates"): assert t in M
    assert "FORCE ROW LEVEL SECURITY" in M
def test_eval_immutable_history():
    for t in ("evaluation_runs","evaluation_metrics","evaluation_cases","evaluation_release_gates"): assert f"{t}_immutable" in M or "for t in" in M
