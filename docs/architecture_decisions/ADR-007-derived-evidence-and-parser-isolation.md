# ADR-007: Derived evidence and parser isolation

## Decision

Treat parser outputs as derived evidence, not as replacements for originals. Preserve page/timestamp/bounding-box citation anchors and create explicit `DERIVED_FROM` lineage. Run untrusted complex document parsers outside the API process.

## Consequences

Original accepted evidence remains immutable and independently auditable. RAG indexes can reference extraction units while retaining a path back to the original object. Parser crashes, malformed documents, or excessive processing do not share the API process failure domain. The system pays additional storage and worker complexity in exchange for provenance, replayability, and security.
