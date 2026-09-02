from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from app.domain.orchestration import EvidencePackBinding


@dataclass(frozen=True, slots=True)
class EvidenceSnapshotItem:
    evidence_key: str
    text: str
    source_type: str
    source_id: str
    source_version: str | None
    authority_rank: int
    confidence: float
    citation: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def content_sha256(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    pack_id: str
    claim_id: str
    items: tuple[EvidenceSnapshotItem, ...]
    contradictions: tuple[dict[str, object], ...] = ()
    assessment: dict[str, object] = field(default_factory=dict)

    @property
    def evidence_keys(self) -> frozenset[str]:
        return frozenset(item.evidence_key for item in self.items)

    @property
    def content_sha256(self) -> str:
        material = "|".join(
            [self.pack_id, self.claim_id]
            + [f"{i.evidence_key}:{i.content_sha256}" for i in sorted(self.items, key=lambda x: x.evidence_key)]
        )
        return sha256(material.encode("utf-8")).hexdigest()


class EvidenceSnapshotProvider(Protocol):
    def load(self, binding: EvidencePackBinding) -> EvidenceSnapshot: ...


class InMemoryEvidenceSnapshotProvider:
    def __init__(self, snapshots: tuple[EvidenceSnapshot, ...]) -> None:
        self._snapshots = {snapshot.pack_id: snapshot for snapshot in snapshots}

    def load(self, binding: EvidencePackBinding) -> EvidenceSnapshot:
        snapshot = self._snapshots.get(binding.pack_id)
        if snapshot is None:
            raise KeyError(f"evidence snapshot not available: {binding.pack_id}")
        if snapshot.claim_id != binding.claim_id:
            raise PermissionError("evidence snapshot claim scope mismatch")
        return snapshot


@dataclass(frozen=True, slots=True)
class EvidenceToolAudit:
    tool_name: str
    input_sha256: str
    result_sha256: str
    result_count: int


class EvidenceOnlyToolbox:
    """Deterministic read-only tools over one immutable evidence snapshot."""

    ALLOWED_TOOLS = frozenset({
        "evidence.list", "evidence.get", "evidence.search", "contradiction.list",
    })

    def __init__(self, snapshot: EvidenceSnapshot) -> None:
        self.snapshot = snapshot
        self.audit: list[EvidenceToolAudit] = []

    def _record(self, name: str, input_text: str, result_text: str, count: int) -> None:
        self.audit.append(EvidenceToolAudit(
            name,
            sha256(input_text.encode()).hexdigest(),
            sha256(result_text.encode()).hexdigest(),
            count,
        ))

    def list_evidence(self) -> tuple[EvidenceSnapshotItem, ...]:
        result = self.snapshot.items
        self._record("evidence.list", self.snapshot.pack_id, "|".join(i.evidence_key for i in result), len(result))
        return result

    def get_evidence(self, evidence_key: str) -> EvidenceSnapshotItem | None:
        result = next((item for item in self.snapshot.items if item.evidence_key == evidence_key), None)
        text = result.content_sha256 if result else "missing"
        self._record("evidence.get", evidence_key, text, int(result is not None))
        return result

    def search_evidence(self, query: str, *, limit: int = 8) -> tuple[EvidenceSnapshotItem, ...]:
        terms = {term.lower() for term in query.split() if len(term) >= 2}
        ranked = []
        for item in self.snapshot.items:
            haystack = item.text.lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append((score, item.authority_rank, item.confidence, item))
        ranked.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
        result = tuple(row[3] for row in ranked[: max(1, min(limit, 20))])
        self._record("evidence.search", query, "|".join(i.evidence_key for i in result), len(result))
        return result

    def list_contradictions(self) -> tuple[dict[str, object], ...]:
        result = self.snapshot.contradictions
        self._record("contradiction.list", self.snapshot.pack_id, repr(result), len(result))
        return result
