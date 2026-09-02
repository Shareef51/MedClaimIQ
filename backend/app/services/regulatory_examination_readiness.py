from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from app.evaluation.regulatory_examination_readiness import readiness_score, detect_evidence_conflicts, validate_cited_draft, immutable_manifest
from app.repositories.regulatory_examination_readiness import RegulatoryExaminationReadinessRepository

class RegulatoryExaminationReadinessService:
    _exams: dict[tuple[str,str], dict] = {}
    _requests: dict[tuple[str,str], dict] = {}
    _evidence: dict[tuple[str,str], list[dict]] = {}
    _drafts: dict[tuple[str,str], list[dict]] = {}
    _packages: dict[tuple[str,str], list[dict]] = {}

    def __init__(self, db, tenant_id: str):
        self.db, self.tenant_id = db, tenant_id
        self.repo = RegulatoryExaminationReadinessRepository(db, tenant_id)

    @staticmethod
    def _id(prefix: str, payload: dict) -> str:
        return prefix + "_" + sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def create_scope(self, actor_id: str, payload: dict) -> dict:
        row = self.repo.tenant_scope({**payload, "created_by": actor_id, "created_at": datetime.now(timezone.utc).isoformat(), "status": "active"})
        self._exams[(self.tenant_id, payload["examination_id"])] = row
        return row

    def create_regulator_request(self, actor_id: str, payload: dict) -> dict:
        if (self.tenant_id, payload["examination_id"]) not in self._exams:
            raise LookupError("examination scope not found")
        request_id = self._id("RR", payload)
        row = self.repo.tenant_scope({**payload, "request_id": request_id, "status": "received", "version": 1, "created_by": actor_id})
        self._requests[(self.tenant_id, request_id)] = row
        return row

    def map_evidence(self, actor_id: str, payload: dict) -> dict:
        key = (self.tenant_id, payload["request_id"])
        if key not in self._requests: raise LookupError("regulator request not found")
        row = self.repo.tenant_scope({**payload, "mapped_by": actor_id, "mapped_at": datetime.now(timezone.utc).isoformat()})
        self._evidence.setdefault(key, []).append(row)
        return row

    def evidence_quality(self, request_id: str) -> dict:
        items = self._evidence.get((self.tenant_id, request_id), [])
        privileged = [x["evidence_id"] for x in items if x.get("evidence_class") in {"legal_privileged", "regulatory_privileged"}]
        conflicts = detect_evidence_conflicts(items)
        return {"request_id": request_id, "evidence_count": len(items), "privileged_evidence_ids": privileged, "segregated_from_standard_response": bool(privileged), **conflicts}

    def create_draft(self, actor_id: str, payload: dict) -> dict:
        key = (self.tenant_id, payload["request_id"])
        if key not in self._requests: raise LookupError("regulator request not found")
        evidence = self._evidence.get(key, [])
        validation = validate_cited_draft(payload, evidence)
        versions = self._drafts.setdefault(key, [])
        row = self.repo.tenant_scope({**payload, "version": len(versions)+1, "status": "human_review_required", "validation": validation, "created_by": actor_id, "human_approval_required": True})
        versions.append(row)
        return row

    def decide_draft(self, actor_id: str, request_id: str, decision: str, rationale: str, expected_version: int) -> dict:
        versions = self._drafts.get((self.tenant_id, request_id), [])
        if not versions: raise LookupError("draft not found")
        current = versions[-1]
        if current["version"] != expected_version: raise ValueError("stale response draft version")
        row = {**current, "version": expected_version+1, "status": "human_approved" if decision == "approve" else decision, "human_decision_by": actor_id, "human_decision_rationale": rationale, "human_decision_at": datetime.now(timezone.utc).isoformat()}
        versions.append(row)
        return row

    def readiness(self, payload: dict) -> dict:
        return {"examination_id": payload["examination_id"], **readiness_score(payload)}

    def build_package(self, actor_id: str, payload: dict) -> dict:
        request_rows = []
        for request_id in payload["request_ids"]:
            req = self._requests.get((self.tenant_id, request_id))
            if not req: raise LookupError(f"request {request_id} not found")
            drafts = self._drafts.get((self.tenant_id, request_id), [])
            if not drafts or drafts[-1].get("status") != "human_approved":
                raise PermissionError("all included responses require explicit human approval")
            request_rows.append({"request_id": request_id, "response_version": drafts[-1]["version"]})
        key = (self.tenant_id, payload["examination_id"])
        versions = self._packages.setdefault(key, [])
        package = self.repo.tenant_scope({**payload, "package_id": self._id("PKG", {**payload, "v":len(versions)+1}), "version": len(versions)+1, "status": "human_submission_approval_required", "requests": request_rows, "created_by": actor_id, "transmit_authority": False})
        package.update(immutable_manifest(package))
        versions.append(package)
        return package

    def decide_package(self, actor_id: str, examination_id: str, decision: str, rationale: str, expected_version: int) -> dict:
        versions = self._packages.get((self.tenant_id, examination_id), [])
        if not versions: raise LookupError("submission package not found")
        current = versions[-1]
        if current["version"] != expected_version: raise ValueError("stale submission package version")
        row = {**current, "version": expected_version+1, "status": "human_approved_for_manual_submission" if decision == "approve" else "rejected", "approved_by": actor_id, "approval_rationale": rationale, "approved_at": datetime.now(timezone.utc).isoformat(), "automated_transmission_permitted": False}
        row.update(immutable_manifest(row))
        versions.append(row)
        return row
