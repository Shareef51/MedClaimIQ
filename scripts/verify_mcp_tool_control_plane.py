from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/mcp.py", "backend/app/mcp/gateway.py", "backend/app/mcp/registry.py",
    "backend/app/mcp/sanitization.py", "backend/app/mcp/circuit.py", "backend/app/mcp/tools.py",
    "backend/app/models/mcp.py", "backend/app/repositories/mcp.py", "backend/app/api/v1/mcp.py",
    "backend/alembic/versions/0014_mcp_tool_control_plane.py", "config/mcp_tool_policy.json",
    "docs/MCP_TOOL_CONTROL_PLANE.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
assert not missing, f"missing MCP artifacts: {missing}"
text = (ROOT / "backend/app/mcp/gateway.py").read_text()
for token in ["required_permission", "allowed_agents", "idempotency", "requires_human_approval", "sanitize_tool_output", "circuit"]:
    assert token in text, token
migration = (ROOT / "backend/alembic/versions/0014_mcp_tool_control_plane.py").read_text()
for table in ["mcp_tool_invocations", "mcp_approval_requests", "mcp_tool_health_events"]:
    assert table in migration
assert "FORCE ROW LEVEL SECURITY" in migration
assert "append_only" in migration
print("MCP tool control plane verification passed")
