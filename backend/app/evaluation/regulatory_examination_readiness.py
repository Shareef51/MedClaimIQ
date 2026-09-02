from __future__ import annotations
from hashlib import sha256
import json

WEIGHTS = {
    "request_coverage": 0.20,
    "evidence_completeness": 0.20,
    "citation_validation": 0.15,
    "conflict_resolution": 0.15,
    "privileged_segregation": 0.10,
    "owner_assignment": 0.10,
    "deadline_health": 0.10,
}

def readiness_score(payload: dict) -> dict:
    score = round(sum(float(payload.get(k, 0)) * w for k, w in WEIGHTS.items()) * 100)
    blockers = [k for k in ("request_coverage", "evidence_completeness", "citation_validation", "conflict_resolution", "privileged_segregation") if float(payload.get(k, 0)) < 1]
    return {"score": score, "ready_for_human_submission_review": score == 100 and not blockers, "blockers": blockers, "decision_authority": "human_only"}

def detect_evidence_conflicts(items: list[dict]) -> dict:
    by_anchor: dict[str, set[str]] = {}
    for item in items:
        by_anchor.setdefault(item.get("citation_anchor", ""), set()).add(item.get("content_hash", ""))
    conflicts = sorted(k for k, v in by_anchor.items() if k and len(v) > 1)
    return {"conflict_detected": bool(conflicts), "anchors": conflicts, "human_resolution_required": bool(conflicts)}

def validate_cited_draft(draft: dict, evidence: list[dict]) -> dict:
    allowed = {e["evidence_id"] for e in evidence if e.get("approved_for_exam_use") and e.get("evidence_class") not in {"legal_privileged", "regulatory_privileged"}}
    missing = sorted(set(draft.get("citation_ids", [])) - allowed)
    return {"passed": not missing and bool(draft.get("citation_ids")), "missing_or_unapproved_citations": missing, "human_approval_required": True}

def immutable_manifest(payload: dict) -> dict:
    digest = sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return {"manifest_hash": digest, "immutable": True}
