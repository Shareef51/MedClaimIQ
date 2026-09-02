# ADR: Bounded Advanced Agentic RAG

## Decision

Use agents and optional model-assisted rewriting only for retrieval planning text. Keep authorization, tenant/claim/ACL scope, temporal restrictions, source authority, knowledge lifecycle eligibility, citation verification, and final answerability gates deterministic.

## Rationale

Query rewriting and HyDE can improve semantic recall, but allowing a model to control security filters or knowledge activation would create a prompt-injection and cross-tenant risk. MedClaimIQ therefore treats model output as untrusted retrieval text and intersects every agent plan with an already authorized scope.

## Consequences

- Model degradation falls back to deterministic planning.
- A planner cannot broaden authorization.
- A second retrieval pass is bounded to two total rounds.
- HyDE text is not evidence and is stored only as a hash in telemetry.
- Citation/gap checks may intentionally return insufficient evidence rather than maximizing answer rate.
