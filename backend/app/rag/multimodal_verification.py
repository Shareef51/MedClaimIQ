from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations

from app.domain.multimodal_rag import InconsistencySeverity, MultimodalCandidate, MultimodalInconsistency

_AMOUNT = re.compile(r"(?<!\w)(?:USD\s*)?[$]?\s*(\d{1,7}(?:\.\d{1,2})?)(?!\w)", re.I)
_CODE = re.compile(r"\b(?:CPT|HCPCS|ICD(?:-10)?|NDC)?\s*[:#-]?\s*([A-Z]?\d{4,7}[A-Z0-9.-]*)\b", re.I)
_DATE = re.compile(r"\b(20\d{2}[-/]\d{2}[-/]\d{2})\b")


class CrossModalVerifier:
    version = "cross-modal-verifier-v1"

    def verify(self, items: list[MultimodalCandidate]) -> tuple[MultimodalInconsistency, ...]:
        facts: dict[str, dict[str, set[str]]] = defaultdict(dict)
        by_id = {item.item_id: item for item in items}
        for item in items:
            text = " ".join((item.text, str(item.metadata.get("fact_text", ""))))
            facts[item.item_id] = {
                "amount": {self._normalize_amount(x) for x in _AMOUNT.findall(text)},
                "code": {x.upper().replace(" ", "") for x in _CODE.findall(text)},
                "date": {x.replace("/", "-") for x in _DATE.findall(text)},
            }

        output: list[MultimodalInconsistency] = []
        for left_id, right_id in combinations(facts, 2):
            left, right = by_id[left_id], by_id[right_id]
            if left.modality == right.modality:
                continue
            for field in ("amount", "code", "date"):
                lvals, rvals = facts[left_id][field], facts[right_id][field]
                if not lvals or not rvals or lvals & rvals:
                    continue
                severity = InconsistencySeverity.MATERIAL if field in {"amount", "code"} else InconsistencySeverity.WARNING
                output.append(MultimodalInconsistency(
                    code=f"cross_modal_{field}_mismatch",
                    field=field,
                    severity=severity,
                    left_item_id=left_id,
                    right_item_id=right_id,
                    left_value=",".join(sorted(lvals))[:300],
                    right_value=",".join(sorted(rvals))[:300],
                    confidence=round(min(left.confidence, right.confidence), 6),
                    description=f"{field} evidence differs across {left.modality.value} and {right.modality.value} sources",
                ))
        return tuple(output[:100])

    @staticmethod
    def _normalize_amount(value: str) -> str:
        try:
            return f"{float(value):.2f}"
        except ValueError:
            return value
