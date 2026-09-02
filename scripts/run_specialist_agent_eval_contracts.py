import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.orchestration import AgentName
from app.agents.prompts import build_prompt_registry

cases = json.loads((ROOT / "sample-data/specialist_agent_eval_cases.json").read_text())
by_agent = {case["agent"] for case in cases}
expected = {agent.value for agent in AgentName}
assert by_agent == expected, f"missing eval fixtures: {sorted(expected - by_agent)}"
prompts = build_prompt_registry()
for case in cases:
    agent = AgentName(case["agent"])
    assert prompts[agent].version == "1.0.0"
    assert case["expected"] in {"supported", "mismatch", "risk", "insufficient_evidence", "review_required"}
print(f"specialist eval contracts verified for {len(cases)} agents")
