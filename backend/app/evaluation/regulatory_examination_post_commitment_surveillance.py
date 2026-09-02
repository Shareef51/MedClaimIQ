from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def sustainability_decay(observations: list[dict], warning_threshold: float = 80.0, critical_threshold: float = 60.0) -> dict:
    if not observations:
        return {"state": "watch", "decay_score": 0.0, "reasons": ["observations_missing"], "reopen_candidate": False}
    ordered = sorted(observations, key=lambda x: int(x.get("days_since_closure", 0)))
    scores = [float(x.get("health_score", 100.0)) for x in ordered]
    latest = scores[-1]
    peak = max(scores)
    decay = round(max(0.0, peak - latest), 2)
    recurrence = any(bool(x.get("recurrence_detected")) for x in ordered)
    failed = any(x.get("control_effective") is False for x in ordered)
    if recurrence or failed or latest < critical_threshold:
        return {"state": "recurrence_candidate", "decay_score": decay, "reasons": ["recurrence_or_effectiveness_failure"], "reopen_candidate": True}
    if latest < warning_threshold or decay >= 15:
        return {"state": "degrading", "decay_score": decay, "reasons": ["sustainability_decay"], "reopen_candidate": True}
    return {"state": "stable", "decay_score": decay, "reasons": [], "reopen_candidate": False}


def match_new_examination(closed_commitment: dict, findings: list[dict]) -> list[dict]:
    matches=[]
    for finding in findings:
        score=0.0
        reasons=[]
        if closed_commitment.get("control_id") and finding.get("control_id")==closed_commitment.get("control_id"):
            score += 0.40; reasons.append("same_control")
        if closed_commitment.get("obligation_id") and finding.get("obligation_id")==closed_commitment.get("obligation_id"):
            score += 0.30; reasons.append("same_obligation")
        if closed_commitment.get("normalized_theme") and finding.get("normalized_theme")==closed_commitment.get("normalized_theme"):
            score += 0.20; reasons.append("same_theme")
        if closed_commitment.get("root_cause_id") and finding.get("root_cause_id")==closed_commitment.get("root_cause_id"):
            score += 0.10; reasons.append("same_root_cause")
        if score >= 0.60:
            matches.append({"finding_id": finding.get("finding_id"), "score": round(score,2), "reasons": reasons, "candidate": True})
    return matches


def cross_entity_recurrence(signals: list[dict], minimum_entities: int = 2) -> dict:
    entity_ids={s.get("entity_id") for s in signals if s.get("entity_id") and (s.get("recurrence_detected") or s.get("control_effective") is False)}
    controls={s.get("control_id") for s in signals if s.get("control_id")}
    candidate=len(entity_ids) >= minimum_entities
    return {"candidate": candidate, "affected_entities": sorted(entity_ids), "affected_controls": sorted(controls), "human_review_required": candidate}


def compare_prior_certification(certification: dict, current_evidence: dict) -> dict:
    prior_score=float(certification.get("effectiveness_score", 100.0))
    current_score=float(current_evidence.get("effectiveness_score", prior_score))
    delta=round(current_score-prior_score,2)
    contradictions=[]
    if certification.get("control_effective") is True and current_evidence.get("control_effective") is False:
        contradictions.append("prior_effective_now_failed")
    if certification.get("scope_entities") and current_evidence.get("scope_entities"):
        missing=sorted(set(certification["scope_entities"])-set(current_evidence["scope_entities"]))
        if missing: contradictions.append("scope_regression:"+",".join(missing))
    return {"prior_score": prior_score, "current_score": current_score, "delta": delta, "contradictions": contradictions, "material_change": bool(contradictions) or delta <= -15}
