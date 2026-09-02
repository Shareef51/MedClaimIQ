from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from app.domain.regulatory_knowledge_governance import KNOWLEDGE_GOVERNANCE_AUTHORITY
from app.evaluation.regulatory_knowledge_governance import readiness_score

class RegulatoryKnowledgeGovernanceService:
    """Tenant-scoped orchestration facade. Persistence adapters can replace the in-process projection without changing API contracts."""
    _nodes: dict[tuple[str, str], dict] = {}
    _edges: list[dict] = []
    _releases: dict[str, list[dict]] = {}

    def __init__(self, db, tenant_id: str):
        self.db, self.tenant_id = db, tenant_id

    def upsert_node(self, actor_id: str, payload: dict) -> dict:
        key = (self.tenant_id, payload["canonical_key"])
        prev = self._nodes.get(key)
        version = 1 if prev is None else prev["version"] + 1
        if payload.get("knowledge_class") == "authoritative":
            raise PermissionError("authoritative knowledge requires explicit human approval workflow")
        row = {**payload, "tenant_id": self.tenant_id, "version": version, "status": payload.get("knowledge_class", "advisory"), "created_by": actor_id}
        row["content_hash"] = sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self._nodes[key] = row
        return row

    def add_edge(self, actor_id: str, payload: dict) -> dict:
        row = {**payload, "tenant_id": self.tenant_id, "created_by": actor_id, "created_at": datetime.now(timezone.utc).isoformat()}
        self._edges.append(row)
        return row

    def approve_knowledge(self, actor_id: str, canonical_key: str, decision: str, rationale: str, expected_version: int) -> dict:
        key = (self.tenant_id, canonical_key)
        row = self._nodes.get(key)
        if not row: raise LookupError("knowledge node not found")
        if row["version"] != expected_version: raise ValueError("stale knowledge version")
        row = dict(row)
        row["version"] += 1
        row["status"] = "authoritative" if decision == "approve" else ("superseded" if decision == "supersede" else "rejected")
        row["approved_by"] = actor_id
        row["approval_rationale"] = rationale
        row["approved_at"] = datetime.now(timezone.utc).isoformat()
        self._nodes[key] = row
        return row

    def query_graph(self, question: str, as_of: str, entity_ids: list[str], regulator: str | None = None) -> dict:
        nodes = [v for (tenant, _), v in self._nodes.items() if tenant == self.tenant_id]
        authoritative = [n for n in nodes if n.get("status") in {"authoritative", "approved_internal"}]
        return {
            "question": question, "as_of": as_of, "entity_ids": entity_ids, "regulator": regulator,
            "answer": "Evidence pack requires human validation before examination use.",
            "citations": [{"canonical_key": n["canonical_key"], "version": n["version"], "knowledge_class": n["status"], "evidence_refs": n.get("evidence_refs", [])} for n in authoritative[:8]],
            "human_validation_required": True,
            "authority": "retrieval_and_analysis_only",
        }

    def readiness(self, payload: dict) -> dict:
        result = readiness_score(payload)
        return {"examination_id": payload["examination_id"], **result}

    def publish_release(self, actor_id: str, release_name: str, approved_keys: list[str]) -> dict:
        rows = [self._nodes[(self.tenant_id, k)] for k in approved_keys if (self.tenant_id, k) in self._nodes]
        if not rows or any(r.get("status") != "authoritative" for r in rows):
            raise PermissionError("knowledge releases may contain only human-approved authoritative knowledge")
        versions = self._releases.setdefault(self.tenant_id, [])
        release = {"release_name": release_name, "release_version": len(versions)+1, "approved_keys": approved_keys, "published_by": actor_id, "immutable": True}
        release["release_hash"] = sha256(json.dumps(release, sort_keys=True).encode()).hexdigest()
        versions.append(release)
        return release
