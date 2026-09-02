from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model: str
    dimensions: int
    input_hashes: list[str]


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch: ...


def embedding_input_hash(*, model: str, dimensions: int, text: str) -> str:
    return hashlib.sha256(f"{model}|{dimensions}|{text}".encode("utf-8")).hexdigest()
