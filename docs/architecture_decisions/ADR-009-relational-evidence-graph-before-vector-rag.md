# ADR: Relational evidence graph is authoritative before vector RAG

## Decision

MedClaimIQ will build a deterministic tenant-scoped canonical evidence graph in PostgreSQL before creating vector indexes. Vector databases are retrieval projections, not systems of record.

## Why

Medical claim verification needs stable identities, exact service-date relationships, immutable source versions, contradiction preservation, authorization metadata, and auditability. A vector-only architecture cannot reliably provide those guarantees.

## Consequences

- Graph construction is deterministic and provenance-backed.
- LLMs may reason over graph results but cannot silently mutate authoritative graph identity/edges.
- Source versions and graph edge history are append-only.
- Human review resolves ambiguous identity/crosswalk/contradiction cases.
- Future GraphRAG can traverse the same relational graph or project it into a specialized graph engine without changing the source of truth.
