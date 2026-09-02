# ADR-005: Claim-Centered Evidence System of Record

## Status

Accepted.

## Decision

MedClaimIQ uses PostgreSQL as the authoritative claim/evidence system of record. Vector indexes and future graph indexes are derived retrieval projections, not authoritative data stores.

Claims reference tenant-local patients, organizations, policies and encounters. Claim lines remain independent structured records. Evidence sources and derived artifacts are immutable-content records connected by append-only lineage edges. Claim status changes, human decisions and audit records are append-only.

A generic automated workflow cannot finalize a claim from `human_review`. A persisted, authorized human decision is required.

## Rationale

Medical-claim verification depends on temporal, financial and relational facts that should be validated deterministically. Keeping those relationships in the system of record allows later RAG and agent reasoning to retrieve evidence instead of reconstructing core facts probabilistically.

## Consequences

- PostgreSQL tenant isolation is enforced using explicit predicates and RLS.
- Evidence derivatives never replace their source artifact.
- Vector/GraphRAG layers must preserve system-of-record identifiers and provenance.
- Lifecycle retries are idempotent and status-versioned.
- Final human decisions retain an evidence snapshot suitable for audit/reconstruction.
