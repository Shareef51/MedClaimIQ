from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from app.security.data_classification import DLPRedactor

_DLP = DLPRedactor()

SENSITIVE_KEYS = {
    "authorization", "cookie", "set-cookie", "password", "secret", "token", "api_key",
    "access_token", "refresh_token", "patient_name", "member_name", "email", "phone",
    "address", "prompt", "input_text", "output_text", "evidence_text", "raw_query", "query",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return sha256_text(value)[:24]


def sanitize_attributes(value: Any, *, depth: int = 0) -> Any:
    """Return telemetry-safe data. Never export raw prompts/evidence/user text."""
    if depth > 5:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in SENSITIVE_KEYS or any(part in lowered for part in ("prompt", "secret", "token", "password", "raw_")):
                if item is None:
                    result[str(key)] = None
                else:
                    result[f"{key}_sha256"] = sha256_text(str(item))
                continue
            result[str(key)] = sanitize_attributes(item, depth=depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_attributes(item, depth=depth + 1) for item in list(value)[:100]]
    if isinstance(value, str):
        safe, _ = _DLP.redact(value[:2048])
        return str(safe)[:512]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:512]
