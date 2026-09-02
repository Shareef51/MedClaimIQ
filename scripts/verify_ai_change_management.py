from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/ai_change_management.py",
    "backend/app/models/ai_change_management.py",
    "backend/app/repositories/ai_change_management.py",
    "backend/app/services/ai_change_management.py",
    "backend/app/api/v1/ai_change_management.py",
    "backend/alembic/versions/0024_ai_change_management.py",
    "config/ai_change_management_policy.json",
    "config/ai_runtime_defaults.json",
    "docs/AI_CONFIGURATION_EXPERIMENTATION_CHANGE_MANAGEMENT.md",
    "sample-data/ai_change_experiment_scenarios.json",
]
missing = [p for p in required if not (ROOT / p).exists()]
assert not missing, f"missing AI change-management artifacts: {missing}"
policy = json.loads((ROOT / "config/ai_change_management_policy.json").read_text())
assert policy["promotion"]["production_requires_passing_evaluation"] is True
assert policy["promotion"]["high_risk_requires_human_approval"] is True
assert policy["promotion"]["prevent_self_approval"] is True
assert policy["experiments"]["shadow_output_can_drive_claim_decision"] is False
assert policy["experiments"]["raw_subject_identifiers_persisted"] is False
assert policy["drift_detection"]["production_drift_blocks_release"] is True
migration = (ROOT / "backend/alembic/versions/0024_ai_change_management.py").read_text()
for table in ("ai_configuration_snapshots", "ai_experiment_assignments", "ai_experiment_observations", "ai_configuration_drift_events", "ai_change_events"):
    assert table in migration
assert "FORCE ROW LEVEL SECURITY" in migration
assert "_immutable" in migration
main = (ROOT / "backend/app/main.py").read_text()
assert "ai-change-management-model" in main and "ai_change_management_router" in main
agent_factory = (ROOT / "backend/app/core/agent_factory.py").read_text()
assert "resolve_agent_runtime_configuration" in agent_factory
print("AI configuration/change-management architecture verifier: PASS")
