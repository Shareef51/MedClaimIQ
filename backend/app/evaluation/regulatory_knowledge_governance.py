from __future__ import annotations
from datetime import datetime, timezone


def temporal_relevance(record: dict, as_of: str) -> dict:
    t = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    effective = datetime.fromisoformat(record["effective_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")) if record.get("expires_at") else None
    applicable = effective <= t and (expires is None or t < expires) and record.get("status") != "superseded"
    return {"applicable": applicable, "as_of": as_of, "version_id": record.get("version_id")}


def detect_knowledge_conflict(items: list[dict]) -> dict:
    active = [x for x in items if x.get("status") in {"authoritative", "approved_internal"}]
    positions = {str(x.get("normalized_position", "")).strip().lower() for x in active if x.get("normalized_position")}
    evidence = sorted({e for x in active for e in x.get("evidence_refs", [])})
    return {
        "conflict_detected": len(positions) > 1,
        "position_count": len(positions),
        "evidence_refs": evidence,
        "human_resolution_required": len(positions) > 1,
    }


def readiness_score(data: dict) -> dict:
    weights = {
        "authoritative_coverage": .30,
        "evidence_freshness": .20,
        "control_lineage_coverage": .20,
        "open_conflict_resolution": .15,
        "historical_finding_coverage": .15,
    }
    score = round(sum(max(0.0, min(1.0, float(data.get(k, 0)))) * w for k, w in weights.items()) * 100, 2)
    return {"score": score, "ready": score >= 85, "human_validation_required": True, "weights": weights}


def evaluate_cited_answer(answer: dict) -> dict:
    citations = answer.get("citations", [])
    claims = answer.get("material_claims", [])
    cited_claims = sum(1 for c in claims if c.get("citation_ids"))
    ratio = 1.0 if not claims else cited_claims / len(claims)
    authoritative = all(c.get("knowledge_class") in {"authoritative", "approved_internal"} for c in citations) if citations else False
    return {
        "citation_completeness": round(ratio, 4),
        "authoritative_support": authoritative,
        "passed": ratio == 1.0 and authoritative,
        "decision_authority": "human_only",
    }
