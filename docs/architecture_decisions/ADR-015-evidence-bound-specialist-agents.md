# ADR-015: Evidence-bound specialist agents

## Decision

Specialist LLM agents are advisory reasoning components bound to immutable evidence packs. They may only use read-only evidence tools and strict structured outputs. Deterministic platform services retain all authoritative mutation capabilities.

## Consequences

- Agent output cannot widen tenant or claim scope.
- Every material finding must cite pack evidence.
- Unknown evidence references fail closed.
- Prompt versions and hashes are reproducible.
- Decision-support outputs remain advisory and require human review.
- Tooling can be audited without exposing unrestricted infrastructure access to the model.
