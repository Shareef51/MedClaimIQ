from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/agents/structured.py", "backend/app/agents/evidence_tools.py",
    "backend/app/agents/prompts.py", "backend/app/agents/model_client.py",
    "backend/app/agents/specialists.py", "backend/app/api/v1/specialist_agents.py",
    "config/specialist_agent_policy.json", "sample-data/specialist_agent_eval_cases.json",
    "docs/PRODUCTION_SPECIALIST_AGENTS.md",
]
for rel in required:
    assert (ROOT / rel).exists(), rel
text = (ROOT / "backend/app/agents/contracts.py").read_text()
assert "database sessions" in text and "final" in text
structured = (ROOT / "backend/app/agents/structured.py").read_text()
assert "final_decision" in structured and "PROHIBITED_STRUCTURED_FIELDS" in structured
specialists = (ROOT / "backend/app/agents/specialists.py").read_text()
assert "unknown evidence keys" in specialists and "build_specialist_registry" in specialists
print("specialist agent architecture verified")
