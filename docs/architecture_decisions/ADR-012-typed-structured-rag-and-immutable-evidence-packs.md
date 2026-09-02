# ADR: Typed structured retrieval and immutable evidence packs

## Decision

MedClaimIQ will not execute LLM-generated SQL, FHIR queries or graph query language. Structured retrieval is represented by typed, whitelisted query plans. Graph traversal is bounded and claim-scoped. Cross-source results are normalized into immutable evidence-pack snapshots with provenance and contradictions preserved.

## Rationale

This prevents prompt content from becoming executable data-access instructions, preserves tenant and claim isolation, makes retrieval reproducible, and gives downstream agent workflows a stable evidence snapshot.

## Consequences

New structured retrieval capabilities require explicit typed repository methods. This is intentionally less flexible than arbitrary SQL generation but substantially safer and easier to evaluate and audit.
