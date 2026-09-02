from pathlib import Path


def test_specialist_agent_audit_migration_has_rls_and_append_only_controls():
    root = Path(__file__).resolve().parents[1]
    text = (root / "alembic/versions/0013_specialist_agent_audit.py").read_text()
    assert "agent_model_invocations" in text
    assert "agent_tool_audits" in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "append_only" in text
