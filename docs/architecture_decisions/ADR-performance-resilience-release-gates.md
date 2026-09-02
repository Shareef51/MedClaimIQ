# ADR — Performance and resilience evidence is part of release quality

## Decision
MedClaimIQ uses deterministic budgets plus controlled live load and failure injection. Performance evidence is versioned and production promotion consumes the SHA-256 of a passing performance report. Chaos is approval-gated and staging-first.

## Rationale
Functional correctness alone does not prove that a claims platform behaves safely under concurrency, backlog, saturation or dependency loss. Conversely, synthetic CI load numbers are not production capacity guarantees. The architecture therefore separates deterministic gate logic from environment-specific live evidence while requiring both before production promotion.

## Safety invariants
Authorization, tenant isolation, evidence integrity and human-final-decision controls have zero tolerance during chaos. Kafka is not the source of truth; transactional outboxes preserve committed events. Qdrant is rebuildable. PostgreSQL business transactions fail closed on database loss.
