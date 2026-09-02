from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.:-][a-z0-9]+)*", re.IGNORECASE)
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "was", "were", "with",
})


@dataclass(frozen=True)
class SparseVectorData:
    indices: tuple[int, ...]
    values: tuple[float, ...]

    def as_lists(self) -> tuple[list[int], list[float]]:
        return list(self.indices), list(self.values)


class SparseEncoder(Protocol):
    name: str

    def encode(self, texts: Sequence[str]) -> list[SparseVectorData]: ...


class HashedBM25SparseEncoder:
    """Dependency-light BM25-compatible lexical encoder for Qdrant sparse vectors.

    Terms are mapped to stable 31-bit feature IDs. Values are log-scaled term frequency;
    Qdrant's sparse-vector IDF modifier supplies corpus-aware inverse document frequency.
    This keeps indexing deterministic and avoids using an LLM for exact-code/keyword recall.
    """

    name = "hashed-bm25-qdrant-idf-v1"

    def __init__(self, *, remove_stop_words: bool = True) -> None:
        self.remove_stop_words = remove_stop_words

    @staticmethod
    def _feature_id(token: str) -> int:
        digest = hashlib.blake2s(token.encode("utf-8"), digest_size=4, person=b"mciqrag").digest()
        return int.from_bytes(digest, "big", signed=False) & 0x7FFFFFFF

    def tokenize(self, text: str) -> list[str]:
        tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
        if self.remove_stop_words:
            tokens = [token for token in tokens if token not in _STOP_WORDS or any(char.isdigit() for char in token)]
        return tokens

    def encode_one(self, text: str) -> SparseVectorData:
        counts = Counter(self.tokenize(text))
        by_index: dict[int, float] = {}
        for token, frequency in counts.items():
            index = self._feature_id(token)
            # BM25-compatible positive term-frequency signal. Qdrant applies IDF.
            value = 1.0 + math.log(max(1, frequency))
            by_index[index] = by_index.get(index, 0.0) + value
        ordered = sorted(by_index.items())
        return SparseVectorData(
            indices=tuple(index for index, _ in ordered),
            values=tuple(value for _, value in ordered),
        )

    def encode(self, texts: Sequence[str]) -> list[SparseVectorData]:
        return [self.encode_one(text) for text in texts]
