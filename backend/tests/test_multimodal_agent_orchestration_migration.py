from pathlib import Path

def test_migration_has_rls_and_immutable_history():
    text=(Path("alembic/versions/0028_multimodal_agent_orchestration.py")).read_text()
    assert 'down_revision="0027_multimodal_rag"' in text
    assert 'ENABLE ROW LEVEL SECURITY' in text and 'FORCE ROW LEVEL SECURITY' in text
    assert 'medclaimiq_reject_immutable_change' in text
    assert 'multimodal_agent_investigations' in text and 'multimodal_agent_events' in text

def test_release_gate_required():
    import json
    policy=json.loads((Path("../config/release_engineering_policy.json")).read_text())
    assert "multimodal-agent-quality" in policy["gates"]["required"]
