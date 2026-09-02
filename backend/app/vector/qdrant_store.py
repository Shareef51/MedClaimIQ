from __future__ import annotations

import uuid
from typing import Sequence

from app.domain.rag import RAGDomain, RetrievalHit, RetrievalScope
from app.sparse.provider import SparseVectorData
from app.vector.store import VectorPoint


class QdrantVectorStore:
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        *,
        url: str,
        api_key: str | None,
        collection_prefix: str,
        index_version: str,
        dimensions: int,
        timeout_seconds: float = 10.0,
        client=None,
    ) -> None:
        if client is None:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=url, api_key=api_key, timeout=timeout_seconds)
        self.client = client
        self.collection_prefix = collection_prefix.rstrip("_")
        self.index_version = index_version
        self.dimensions = dimensions

    def collection_name(self, domain: RAGDomain) -> str:
        safe_version = self.index_version.replace(".", "_").replace("-", "_")
        return f"{self.collection_prefix}_{domain.value}_{safe_version}"

    @staticmethod
    def point_id(chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"medclaimiq:rag:{chunk_id}"))

    def ensure_domain(self, domain: RAGDomain) -> str:
        from qdrant_client import models

        name = self.collection_name(domain)
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config={
                    self.DENSE_VECTOR_NAME: models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    self.SPARSE_VECTOR_NAME: models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
        info = self.client.get_collection(name)
        payload_schema = dict(getattr(info, "payload_schema", {}) or {})
        keyword_fields = (
            "tenant_id", "claim_id", "patient_subject_id", "domain", "source_type",
            "source_id", "source_version", "acl_tags", "entity_ids", "active",
        )
        for field_name in keyword_fields:
            if field_name not in payload_schema:
                self.client.create_payload_index(
                    collection_name=name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
        if "service_date" not in payload_schema:
            self.client.create_payload_index(
                collection_name=name,
                field_name="service_date",
                field_schema=models.PayloadSchemaType.DATETIME,
                wait=True,
            )
        if "authority_rank" not in payload_schema:
            self.client.create_payload_index(
                collection_name=name,
                field_name="authority_rank",
                field_schema=models.PayloadSchemaType.INTEGER,
                wait=True,
            )
        return name

    def upsert(self, domain: RAGDomain, points: Sequence[VectorPoint]) -> None:
        from qdrant_client import models

        if not points:
            return
        name = self.ensure_domain(domain)
        qpoints = []
        for point in points:
            vectors: dict[str, object] = {self.DENSE_VECTOR_NAME: point.vector}
            if point.sparse_vector is not None:
                indices, values = point.sparse_vector.as_lists()
                vectors[self.SPARSE_VECTOR_NAME] = models.SparseVector(indices=indices, values=values)
            qpoints.append(models.PointStruct(id=point.point_id, vector=vectors, payload=point.payload))
        self.client.upsert(collection_name=name, points=qpoints, wait=True)

    def delete_source(self, domain: RAGDomain, *, tenant_id: str, source_id: str, source_version: str | None = None) -> None:
        from qdrant_client import models

        name = self.ensure_domain(domain)
        must = [
            models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id)),
            models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id)),
        ]
        if source_version is not None:
            must.append(models.FieldCondition(key="source_version", match=models.MatchValue(value=source_version)))
        self.client.delete(
            collection_name=name,
            points_selector=models.FilterSelector(filter=models.Filter(must=must)),
            wait=True,
        )

    @staticmethod
    def _filter(scope: RetrievalScope):
        from qdrant_client import models

        must = [
            models.FieldCondition(key="tenant_id", match=models.MatchValue(value=scope.tenant_id)),
            models.FieldCondition(key="active", match=models.MatchValue(value=True)),
        ]
        if scope.claim_id:
            must.append(models.FieldCondition(key="claim_id", match=models.MatchValue(value=scope.claim_id)))
        if scope.patient_subject_id:
            must.append(models.FieldCondition(key="patient_subject_id", match=models.MatchValue(value=scope.patient_subject_id)))
        if scope.acl_tags:
            must.append(models.FieldCondition(key="acl_tags", match=models.MatchAny(any=list(scope.acl_tags))))
        if scope.entity_ids:
            must.append(models.FieldCondition(key="entity_ids", match=models.MatchAny(any=list(scope.entity_ids))))
        if scope.source_types:
            must.append(models.FieldCondition(key="source_type", match=models.MatchAny(any=list(scope.source_types))))
        if scope.service_date_from or scope.service_date_to:
            must.append(
                models.FieldCondition(
                    key="service_date",
                    range=models.DatetimeRange(
                        gte=scope.service_date_from.isoformat() if scope.service_date_from else None,
                        lte=scope.service_date_to.isoformat() if scope.service_date_to else None,
                    ),
                )
            )
        if scope.minimum_authority_rank > 0:
            must.append(
                models.FieldCondition(
                    key="authority_rank",
                    range=models.Range(gte=scope.minimum_authority_rank),
                )
            )
        return models.Filter(must=must)

    @staticmethod
    def _hits(points, *, domain: RAGDomain, source: str) -> list[RetrievalHit]:
        hits: list[RetrievalHit] = []
        for point in points:
            payload = dict(point.payload or {})
            score = float(point.score)
            hits.append(
                RetrievalHit(
                    chunk_id=str(payload.get("chunk_id", point.id)),
                    domain=RAGDomain(str(payload.get("domain", domain.value))),
                    score=score,
                    text=str(payload.get("text", "")),
                    parent_chunk_id=str(payload["parent_chunk_id"]) if payload.get("parent_chunk_id") else None,
                    citation=dict(payload.get("citation") or {}),
                    metadata=dict(payload.get("metadata") or {}),
                    dense_score=score if source == "dense" else None,
                    sparse_score=score if source == "sparse" else None,
                    retrieval_sources=(source,),
                )
            )
        return hits

    def query_dense(self, domain: RAGDomain, *, vector: list[float], scope: RetrievalScope, limit: int) -> list[RetrievalHit]:
        if limit <= 0:
            return []
        name = self.ensure_domain(domain)
        response = self.client.query_points(
            collection_name=name,
            query=vector,
            using=self.DENSE_VECTOR_NAME,
            query_filter=self._filter(scope),
            limit=limit,
            with_payload=True,
        )
        points = getattr(response, "points", response)
        return self._hits(points, domain=domain, source="dense")

    def query_sparse(self, domain: RAGDomain, *, vector: SparseVectorData, scope: RetrievalScope, limit: int) -> list[RetrievalHit]:
        from qdrant_client import models

        if limit <= 0 or not vector.indices:
            return []
        name = self.ensure_domain(domain)
        indices, values = vector.as_lists()
        response = self.client.query_points(
            collection_name=name,
            query=models.SparseVector(indices=indices, values=values),
            using=self.SPARSE_VECTOR_NAME,
            query_filter=self._filter(scope),
            limit=limit,
            with_payload=True,
        )
        points = getattr(response, "points", response)
        return self._hits(points, domain=domain, source="sparse")

    # Backward-compatible dense retrieval method retained for callers from the foundation layer.
    def query(self, domain: RAGDomain, *, vector: list[float], scope: RetrievalScope, limit: int) -> list[RetrievalHit]:
        return self.query_dense(domain, vector=vector, scope=scope, limit=limit)
