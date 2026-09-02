from pathlib import Path


def test_mcp_migration_has_rls_and_immutable_audit_contracts():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend/alembic/versions/0014_mcp_tool_control_plane.py").read_text()
    for table in ("mcp_tool_invocations", "mcp_approval_requests", "mcp_tool_health_events"):
        assert table in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "medclaimiq_reject_mcp_audit_mutation" in text
    assert "mcp_tool_invocations" in text and "mcp_tool_health_events" in text
