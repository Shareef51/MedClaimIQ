from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.fhir_canonical import CanonicalPatient, normalize_patient


@dataclass(frozen=True)
class IdentityMatch:
    score: float
    decision: str
    reasons: tuple[str, ...]


class IdentityReconciler:
    """Deterministic identity candidate scoring; ambiguous matches require human review."""

    MATCH_THRESHOLD = 0.90
    REVIEW_THRESHOLD = 0.70

    def compare(self, internal: dict[str, Any], fhir_patient: dict[str, Any]) -> IdentityMatch:
        external: CanonicalPatient = normalize_patient(fhir_patient)
        score = 0.0
        reasons: list[str] = []
        internal_ids = {str(v) for v in (internal.get("identifiers") or []) if v}
        external_ids = set(external.identifiers)
        if internal_ids and external_ids and internal_ids.intersection(external_ids):
            score += 0.60
            reasons.append("identifier_match")
        if internal.get("birth_date") and internal.get("birth_date") == external.birth_date:
            score += 0.20
            reasons.append("birth_date_match")
        internal_family = str(internal.get("family_name") or "").strip().lower()
        external_family = str(external.family_name or "").strip().lower()
        if internal_family and external_family:
            similarity = SequenceMatcher(None, internal_family, external_family).ratio()
            score += 0.20 * similarity
            if similarity >= 0.9:
                reasons.append("family_name_match")
        score = round(min(score, 1.0), 4)
        if score >= self.MATCH_THRESHOLD:
            decision = "matched"
        elif score >= self.REVIEW_THRESHOLD:
            decision = "review_required"
        else:
            decision = "rejected"
        return IdentityMatch(score=score, decision=decision, reasons=tuple(reasons))
