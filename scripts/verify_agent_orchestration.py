from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/orchestration.py",
    "backend/app/agents/contracts.py",
    "backend/app/orchestration/langgraph_runtime.py",
    "backend/app/orchestration/checkpoint.py",
    "backend/app/orchestration/router.py",
    "backend/app/models/orchestration.py",
    "backend/app/repositories/orchestration.py",
    "backend/app/services/orchestration.py",
    "backend/app/api/v1/orchestration.py",
    "backend/alembic/versions/0012_langgraph_agent_orchestration.py",
    "config/agent_orchestration_policy.json",
    "docs/LANGGRAPH_DURABLE_AGENT_ORCHESTRATION.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
assert not missing, f"missing orchestration artifacts: {missing}"

runtime = (ROOT / "backend/app/orchestration/langgraph_runtime.py").read_text()
assert "Send" in runtime and "interrupt" in runtime and "operator.add" in runtime
contracts = (ROOT / "backend/app/agents/contracts.py").read_text()
assert "database sessions" in contracts.lower() and "final" in contracts.lower()
migration = (ROOT / "backend/alembic/versions/0012_langgraph_agent_orchestration.py").read_text()
assert "FORCE ROW LEVEL SECURITY" in migration
assert "immutable agent orchestration audit record" in migration
print("Agent orchestration architecture verification passed")
