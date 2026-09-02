# ADR-008: Versioned FHIR Evidence Boundary

## Status
Accepted

## Decision
MedClaimIQ will isolate hospital interoperability behind a FHIR gateway and persist immutable, version-addressable snapshots before using external healthcare data in verification or retrieval.

The gateway is R4-compatible for the portfolio implementation and exposes a SMART-ready backend-services token boundary. Resource identity is `(connection, resourceType, logical id, meta.versionId)`.

Patient linkage is a separate auditable reconciliation step. FHIR payloads never directly overwrite internal patient/claim records, and ambiguous identity matches require human review.

## Consequences
This preserves source provenance, permits replay against historical versions, reduces cross-system identity risk, and provides future Structured RAG/GraphRAG with stable healthcare relationships.
