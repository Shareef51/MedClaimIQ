from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PHI_RESTRICTED = "phi_restricted"
    SECRET = "secret"


PHI_KEYS = frozenset({
    "patient_name", "member_name", "patient_id", "mrn", "medical_record_number",
    "date_of_birth", "dob", "diagnosis", "diagnosis_code", "procedure_code",
    "claim_number", "policy_number", "subscriber_id", "address", "phone", "email",
})
SECRET_KEYS = frozenset({
    "authorization", "access_token", "refresh_token", "token", "api_key", "apikey",
    "secret", "password", "cookie", "private_key", "client_secret",
})

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_MRN = re.compile(r"\b(?:MRN|Medical\s*Record(?:\s*Number)?)\s*[:#-]?\s*[A-Z0-9-]{4,}\b", re.I)


@dataclass(frozen=True)
class DLPFinding:
    path: str
    classification: DataClassification
    detector: str
    value_sha256: str


class DLPRedactor:
    """Recursive deterministic DLP/redaction boundary.

    Operational telemetry and exports should use this before crossing a lower-trust
    boundary. The implementation records hashes, never the detected PHI/secret value.
    """

    def classify_key(self, key: str) -> DataClassification:
        normalized = key.lower().strip()
        if normalized in SECRET_KEYS or any(part in normalized for part in ("secret", "token", "password", "private_key")):
            return DataClassification.SECRET
        if normalized in PHI_KEYS or any(part in normalized for part in ("patient", "member", "diagnosis", "mrn", "claim_number")):
            return DataClassification.PHI_RESTRICTED
        return DataClassification.INTERNAL

    def redact(self, value: Any, *, path: str = "$", minimum: DataClassification = DataClassification.PHI_RESTRICTED) -> tuple[Any, list[DLPFinding]]:
        findings: list[DLPFinding] = []

        def walk(item: Any, current: str, key_hint: str | None = None) -> Any:
            if isinstance(item, dict):
                out: dict[str, Any] = {}
                for key, child in item.items():
                    classification = self.classify_key(str(key))
                    child_path = f"{current}.{key}"
                    if classification in {DataClassification.PHI_RESTRICTED, DataClassification.SECRET}:
                        findings.append(self._finding(child_path, classification, f"key:{key}", child))
                        out[str(key)] = "[REDACTED_SECRET]" if classification is DataClassification.SECRET else "[REDACTED_PHI]"
                    else:
                        out[str(key)] = walk(child, child_path, str(key))
                return out
            if isinstance(item, list):
                return [walk(child, f"{current}[{index}]", key_hint) for index, child in enumerate(item)]
            if isinstance(item, str):
                text = item
                detectors = (("ssn", _SSN), ("mrn", _MRN), ("email", _EMAIL), ("phone", _PHONE))
                for detector, pattern in detectors:
                    for match in list(pattern.finditer(text)):
                        findings.append(self._finding(current, DataClassification.PHI_RESTRICTED, detector, match.group(0)))
                    text = pattern.sub("[REDACTED_PHI]", text)
                return text
            return item

        return walk(value, path), findings

    @staticmethod
    def _finding(path: str, classification: DataClassification, detector: str, value: Any) -> DLPFinding:
        digest = hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()
        return DLPFinding(path=path, classification=classification, detector=detector, value_sha256=digest)
