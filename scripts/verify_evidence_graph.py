from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/evidence_graph.py",
    "backend/app/models/evidence_graph.py",
    "backend/app/services/evidence_graph.py",
    "backend/app/repositories/evidence_graph.py",
    "backend/app/api/v1/evidence_graph.py",
    "backend/alembic/versions/0007_unified_evidence_graph.py",
    "config/evidence_graph_policy.json",
    "docs/UNIFIED_HEALTHCARE_EVIDENCE_GRAPH.md",
    "sample-data/evidence_graph_seed.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit(f"missing evidence graph files: {missing}")
policy = json.loads((ROOT / "config/evidence_graph_policy.json").read_text())
assert policy["construction"] == "deterministic"
assert policy["guardrails"]["cross_tenant_edges_forbidden"] is True
assert policy["guardrails"]["llm_authoritative_graph_writes"] is False
migration = (ROOT / "backend/alembic/versions/0007_unified_evidence_graph.py").read_text()
assert "ENABLE ROW LEVEL SECURITY" in migration and "FORCE ROW LEVEL SECURITY" in migration
print("Unified evidence graph architecture verified")
