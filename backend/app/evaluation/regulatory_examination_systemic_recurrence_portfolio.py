from __future__ import annotations
import hashlib, json
from collections import Counter, defaultdict


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def aggregate_systemic_patterns(occurrences: list[dict]) -> dict:
    root_causes = Counter(x.get("root_cause_id") for x in occurrences if x.get("root_cause_id"))
    controls = Counter(x.get("control_id") for x in occurrences if x.get("control_id"))
    entities = {x.get("entity_id") for x in occurrences if x.get("entity_id")}
    exams = {x.get("examination_id") for x in occurrences if x.get("examination_id")}
    commitments = {x.get("commitment_id") for x in occurrences if x.get("commitment_id")}
    regulators = {x.get("regulator") for x in occurrences if x.get("regulator")}
    shared_root_causes = [{"root_cause_id": k, "occurrence_count": v} for k, v in root_causes.items() if v >= 2]
    systemic_controls = [{"control_id": k, "occurrence_count": v} for k, v in controls.items() if v >= 2]
    candidate = len(commitments) >= 3 and (bool(shared_root_causes) or bool(systemic_controls) or len(entities) >= 3)
    return {
        "recurring_commitment_count": len(commitments), "affected_entity_count": len(entities),
        "affected_examination_count": len(exams), "regulator_count": len(regulators),
        "shared_root_causes": shared_root_causes, "systemic_control_clusters": systemic_controls,
        "systemic_pattern_candidate": candidate, "human_confirmation_required": candidate,
    }


def supervisory_materiality_score(payload: dict) -> dict:
    commitments = min(int(payload.get("recurring_commitment_count", 0)), 10)
    entities = min(int(payload.get("affected_entity_count", 0)), 10)
    controls = min(int(payload.get("affected_control_count", 0)), 10)
    exams = min(int(payload.get("affected_examination_count", 0)), 10)
    regulators = min(int(payload.get("regulator_count", 0)), 5)
    critical = min(int(payload.get("critical_control_count", 0)), 10)
    overdue = min(int(payload.get("overdue_follow_up_count", 0)), 10)
    repeated_root = bool(payload.get("repeated_root_cause", False))
    score = min(100, commitments*4 + entities*4 + controls*3 + exams*3 + regulators*5 + critical*4 + overdue*3 + (15 if repeated_root else 0))
    level = "critical" if score >= 80 else "high" if score >= 60 else "moderate" if score >= 35 else "low"
    return {
        "materiality_score": score, "materiality_level": level,
        "enterprise_intervention_required": score >= 60,
        "executive_review_required": score >= 60,
        "internal_audit_challenge_required": score >= 80 or (score >= 60 and repeated_root),
        "authoritative_regulatory_conclusion": False,
    }


def correlate_regulator_followups(occurrences: list[dict], followups: list[dict]) -> dict:
    by_commitment = defaultdict(list)
    for f in followups:
        if f.get("commitment_id"): by_commitment[f["commitment_id"]].append(f)
    linked = sum(1 for x in occurrences if x.get("commitment_id") in by_commitment)
    overdue = sum(1 for fs in by_commitment.values() for f in fs if f.get("overdue") is True)
    return {"linked_occurrence_count": linked, "overdue_follow_up_count": overdue, "human_interpretation_required": True}
