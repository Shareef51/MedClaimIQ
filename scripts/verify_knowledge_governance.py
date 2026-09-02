#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/knowledge_governance.py", "backend/app/models/knowledge_governance.py",
    "backend/app/repositories/knowledge_governance.py", "backend/app/services/knowledge_governance.py",
    "backend/app/workers/knowledge_reindex.py", "backend/app/api/v1/knowledge_governance.py",
    "backend/alembic/versions/0025_knowledge_lifecycle_governance.py",
    "config/knowledge_governance_policy.json", "docs/KNOWLEDGE_LIFECYCLE_GOVERNANCE.md",
    "scripts/run_knowledge_reindex.py", "scripts/scan_knowledge_projection_drift.py",
]
missing = [item for item in required if not (ROOT/item).exists()]
if missing:
    raise SystemExit("missing knowledge governance artifacts: " + ", ".join(missing))
policy = json.loads((ROOT/"config/knowledge_governance_policy.json").read_text())
assert policy["projection"]["database_is_authoritative"] is True
assert policy["projection"]["vector_store_is_rebuildable"] is True
assert policy["approval"]["prevent_self_approval"] is True
service = (ROOT/"backend/app/services/knowledge_governance.py").read_text()
worker = (ROOT/"backend/app/workers/knowledge_reindex.py").read_text()
assert "blocking retrieval drift" in service
assert "temporally_valid" in service
assert "stale_chunk_ids" in service and "stale_chunk_ids" in worker
assert "delete_source" in worker and "deactivate_source" in worker
print("knowledge governance verifier: PASS")
