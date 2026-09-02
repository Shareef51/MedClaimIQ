from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VisualDescriptorProvider(Protocol):
    """Provider-neutral visual descriptor boundary.

    Implementations may use an approved vision model, but descriptors are treated as derived,
    untrusted evidence metadata and never as authoritative claim facts by themselves.
    """

    def describe(self, path: Path, *, media_type: str) -> dict[str, object]: ...


def sanitize_visual_descriptor(payload: dict[str, object] | None) -> dict[str, object]:
    payload = dict(payload or {})
    text = str(payload.get("description") or "").strip()[:4000]
    labels = [str(x).strip()[:120] for x in list(payload.get("labels") or [])[:30] if str(x).strip()]
    return {
        "description": text,
        "labels": labels,
        "provider": str(payload.get("provider") or "configured-vision-adapter")[:120],
        "model": str(payload.get("model") or "")[:160],
    }
