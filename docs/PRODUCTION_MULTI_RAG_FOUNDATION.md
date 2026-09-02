# Production Multi-RAG Foundation

MedClaimIQ treats retrieval as a governed evidence subsystem, not as a generic vector search feature.
PostgreSQL is authoritative for chunks, source versions, index jobs, projection manifests and citations.
Qdrant stores rebuildable dense-vector projections separated by RAG domain.

## Retrieval domains

- Claim RAG
- Policy RAG
- Hospital RAG
- Invoice RAG
- Coding RAG
- Historical Claims RAG
- Evidence RAG

## Parent/child retrieval

Layout-aware extraction units are converted into parent and child chunks. Parent chunks preserve broad
context. Child/table/transcript chunks are embedded and searched. A dense hit can hydrate its parent
without replacing the citation anchor from the matched child.

Every chunk preserves the original evidence ID, extraction-unit ID, page number, bounding box or media
timestamp when available, plus source version/content hash, canonical entity IDs, graph relationship types,
authority rank, evidence confidence and ACL tags.

## Security filtering

`tenant_id` is mandatory. Normal claim retrieval additionally carries `claim_id` and effective ACL tags.
Qdrant filters are applied during vector retrieval; cross-tenant results are not retrieved and then filtered
in application memory. PostgreSQL RLS protects the authoritative chunk/job tables independently.

JWT-provided tenant/role claims are not used to build RAG filters. Effective authorization must come from
the persisted principal and claim authorization layer implemented elsewhere in MedClaimIQ.

## Embeddings

The OpenAI adapter defaults to `text-embedding-3-large` with a configurable dimension. Embeddings are
batched and cached by a hash of model + dimensions + normalized input text. API keys belong in environment
secret injection/secret management and are never persisted in chunk records.

## Vector projection lifecycle

1. Persist deterministic chunks in PostgreSQL.
2. Embed child/table/transcript chunks.
3. Upsert deterministic UUID points to a domain-specific Qdrant collection.
4. Persist the Qdrant point/collection/model/index-version manifest.
5. On re-index, delete old source projections and deactivate old PostgreSQL versions before upserting the new version.
6. On failure, retry with exponential backoff and persist terminal failures to a DLQ.

This deliberately avoids pretending PostgreSQL and Qdrant share a distributed transaction. Qdrant is a
rebuildable projection and indexing is replay-safe.

## Scope of this foundation

This layer implements dense retrieval. Sparse/BM25 retrieval, hybrid fusion, reranking, query rewriting,
Structured RAG, GraphRAG traversal and self-corrective retrieval are intentionally layered above this
foundation rather than hidden inside the first vector implementation.

## Authenticated dense search API

`POST /api/v1/claims/{claim_id}/rag/search` requires the normal OIDC bearer token and `X-Tenant-Id`.
The API first performs persisted claim authorization. It then derives `claim_authorized`, role and user ACL
tags from the server-resolved principal. Tenant IDs and ACL tags are not accepted from the request body.
The request can choose retrieval domains, entity filters and `top_k`, but cannot widen authorization scope.
