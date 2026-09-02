from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "backend/app/orchestration/engine.py",
    ROOT / "backend/app/orchestration/runner.py",
    ROOT / "backend/app/orchestration/evidence_hydration.py",
    ROOT / "backend/app/orchestration/streaming.py",
    ROOT / "config/end_to_end_agent_execution_policy.json",
    ROOT / "docs/END_TO_END_AGENT_EXECUTION.md",
    ROOT / "sample-data/end_to_end_agent_workflow_scenario.json",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
if missing:
    raise SystemExit(f"missing end-to-end execution artifacts: {missing}")

engine = (ROOT / "backend/app/orchestration/engine.py").read_text()
for token in [
    '"hydrate_evidence"', '"supervisor"', '"intake"', '"specialist"',
    '"evidence_fusion"', '"critic"', '"decision_support"',
    '"human_review_router"', '"human_gate"', "Send(", "interrupt(",
]:
    if token not in engine:
        raise SystemExit(f"execution engine is missing required contract token: {token}")

api = (ROOT / "backend/app/api/v1/orchestration.py").read_text()
for token in ["/execute", "/events", "StreamingResponse", "CLAIM_REVIEW"]:
    if token not in api:
        raise SystemExit(f"orchestration API is missing: {token}")

print("End-to-end LangGraph execution architecture verification passed.")
