from __future__ import annotations

from typing import Sequence

from app.embeddings.cache import EmbeddingCache
from app.embeddings.provider import EmbeddingProvider, embedding_input_hash


class CachedBatchEmbedder:
    def __init__(self, provider: EmbeddingProvider, cache: EmbeddingCache, *, batch_size: int = 64, ttl_seconds: int = 86400) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.provider = provider
        self.cache = cache
        self.batch_size = batch_size
        self.ttl_seconds = ttl_seconds

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            key = embedding_input_hash(model=self.provider.model, dimensions=self.provider.dimensions, text=text.replace("\n", " ").strip())
            cached = self.cache.get(key)
            if cached is not None:
                results[index] = cached
            else:
                missing.append((index, text, key))

        for offset in range(0, len(missing), self.batch_size):
            batch = missing[offset: offset + self.batch_size]
            response = self.provider.embed([item[1] for item in batch])
            for (index, _text, key), vector in zip(batch, response.vectors, strict=True):
                self.cache.set(key, vector, self.ttl_seconds)
                results[index] = vector

        if any(vector is None for vector in results):
            raise RuntimeError("embedding cache/provider failed to populate every vector")
        return [vector for vector in results if vector is not None]
