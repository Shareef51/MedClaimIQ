# ADR: Govern knowledge as immutable releases and keep vector stores rebuildable

## Decision

Knowledge source versions are immutable, independently approved, temporally bounded artifacts. Production retrieval eligibility is established by an approved knowledge release, not by the presence of a vector in Qdrant. PostgreSQL governance state is authoritative; Qdrant and embedding projections are disposable/rebuildable.

## Consequences

- model/index migrations can re-embed existing chunks without re-ingesting original evidence;
- stale projections can be detected deterministically from content/config hashes;
- retirement propagates to the vector layer without erasing audit history;
- retrieval quality regressions can block a knowledge release;
- release manifests identify exact source versions used by production RAG.
