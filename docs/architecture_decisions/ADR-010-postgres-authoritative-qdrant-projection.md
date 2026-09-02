# ADR: PostgreSQL is authoritative; Qdrant is a rebuildable RAG projection

## Decision

Persist chunk text, lineage metadata, source versions, index jobs and vector projection manifests in
PostgreSQL. Store dense embeddings and filterable payloads in domain-separated Qdrant collections.

## Rationale

Medical-claims evidence requires durable provenance, tenant isolation and replayable lifecycle semantics.
A vector database is optimized for retrieval, not for being the authoritative audit/provenance database.
Deterministic chunk and Qdrant point IDs make retry/upsert operations idempotent and allow the complete
vector index to be rebuilt from PostgreSQL.

## Consequences

- Vector indexing is eventually consistent with PostgreSQL.
- Retrieval health must expose index lag later in the observability layer.
- Re-index/delete operations are explicit jobs with retry/DLQ semantics.
- Source/version metadata is mandatory in Qdrant payloads.
- Retrieval must always apply tenant/claim/ACL filters before returning hits.
