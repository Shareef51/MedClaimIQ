from __future__ import annotations

import json
from typing import Protocol


class EmbeddingCache(Protocol):
    def get(self, key: str) -> list[float] | None: ...
    def set(self, key: str, vector: list[float], ttl_seconds: int) -> None: ...


class MemoryEmbeddingCache:
    def __init__(self) -> None:
        self.values: dict[str, list[float]] = {}

    def get(self, key: str) -> list[float] | None:
        vector = self.values.get(key)
        return list(vector) if vector is not None else None

    def set(self, key: str, vector: list[float], ttl_seconds: int) -> None:
        self.values[key] = list(vector)


class RedisEmbeddingCache:
    def __init__(self, client, *, prefix: str = "medclaimiq:embedding:") -> None:
        self.client = client
        self.prefix = prefix

    def get(self, key: str) -> list[float] | None:
        value = self.client.get(self.prefix + key)
        if value is None:
            return None
        payload = json.loads(value)
        return [float(item) for item in payload]

    def set(self, key: str, vector: list[float], ttl_seconds: int) -> None:
        self.client.setex(self.prefix + key, ttl_seconds, json.dumps(vector, separators=(",", ":")))
