from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from app.domain.rag import RAGDomain, RetrievalHit, RetrievalScope
from app.sparse.provider import SparseVectorData


@dataclass(frozen=True)
class VectorPoint:
    point_id: str
    vector: list[float]
    payload: dict[str, object]
    sparse_vector: SparseVectorData | None = None


class VectorStore(Protocol):
    def ensure_domain(self, domain: RAGDomain) -> str: ...
    def upsert(self, domain: RAGDomain, points: Sequence[VectorPoint]) -> None: ...
    def delete_source(self, domain: RAGDomain, *, tenant_id: str, source_id: str, source_version: str | None = None) -> None: ...
    def query_dense(self, domain: RAGDomain, *, vector: list[float], scope: RetrievalScope, limit: int) -> list[RetrievalHit]: ...
    def query_sparse(self, domain: RAGDomain, *, vector: SparseVectorData, scope: RetrievalScope, limit: int) -> list[RetrievalHit]: ...
    def query(self, domain: RAGDomain, *, vector: list[float], scope: RetrievalScope, limit: int) -> list[RetrievalHit]: ...
