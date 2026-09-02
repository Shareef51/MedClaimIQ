from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

_SECRET_KEY = re.compile(r"(authorization|password|secret|token|api[_-]?key|cookie|set-cookie)", re.I)
_INJECTION_PATTERNS = (
    re.compile(r"\b(ignore|disregard)\b.{0,40}\b(previous|system|developer|instructions?)\b", re.I | re.S),
    re.compile(r"\b(reveal|show)\b.{0,30}\b(system prompt|developer message|hidden instructions?)\b", re.I | re.S),
    re.compile(r"\b(call|invoke|execute|run)\b.{0,30}\b(tool|function|shell|command)\b", re.I | re.S),
    re.compile(r"(<\|system\|>|\[system\]|BEGIN SYSTEM|###\s*SYSTEM)", re.I),
)


@dataclass(frozen=True, slots=True)
class SanitizationReport:
    value: Any
    sanitized: bool
    redacted_keys: tuple[str, ...]
    injection_paths: tuple[str, ...]
    output_sha256: str


def _sanitize(value: Any, path: str, redacted: list[str], injections: list[str]) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if _SECRET_KEY.search(key_text) and item is not None:
                clean[key_text] = "[REDACTED]"
                redacted.append(child_path)
            else:
                clean[key_text] = _sanitize(item, child_path, redacted, injections)
        return clean
    if isinstance(value, list):
        return [_sanitize(item, f"{path}[{index}]", redacted, injections) for index, item in enumerate(value)]
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _INJECTION_PATTERNS):
            injections.append(path or "$value")
            return "[UNTRUSTED_TOOL_TEXT_BLOCKED]"
        return value
    return value


def sanitize_tool_output(value: Any) -> SanitizationReport:
    redacted: list[str] = []
    injections: list[str] = []
    clean = _sanitize(value, "", redacted, injections)
    material = repr(clean).encode("utf-8")
    return SanitizationReport(
        value=clean,
        sanitized=bool(redacted or injections),
        redacted_keys=tuple(sorted(redacted)),
        injection_paths=tuple(sorted(injections)),
        output_sha256=sha256(material).hexdigest(),
    )
