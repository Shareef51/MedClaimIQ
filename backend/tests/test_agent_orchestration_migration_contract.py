from pathlib import Path

MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "0012_langgraph_agent_orchestration.py"


def test_agent_orchestration_migration_has_tenant_rls_and_audit_tables():
    source = MIGRATION.read_text()
    for table in (
        "agent_workflows", "agent_executions", "agent_findings", "agent_human_checkpoints", "agent_workflow_events",
    ):
        assert table in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.current_tenant_id'" in source
    assert "immutable agent orchestration audit record" in source
    assert "uq_agent_workflow_event_idempotency" in source
