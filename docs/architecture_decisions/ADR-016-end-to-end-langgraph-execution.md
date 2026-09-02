# ADR-016: Execute specialists through one durable evidence-bound LangGraph

## Status

Accepted.

## Decision

MedClaimIQ compiles one durable LangGraph for claim investigation: evidence hydration, deterministic supervision, intake, parallel specialist branches, evidence fusion, critic review, advisory decision support, human-review routing, and a durable human interrupt.

The authoritative evidence pack is rehydrated and hash-verified before model use. Parallel specialists operate as isolated failure domains and only reducer-backed findings are merged across branches. PostgreSQL remains authoritative for workflow/audit state and the LangGraph PostgreSQL checkpointer owns graph checkpoint persistence.

The human checkpoint is deliberately outside model authority. Final claim decisions continue through the deterministic claim-domain service after authorized human review.

## Consequences

- Workflows are replayable against a stable evidence boundary.
- A failed specialist does not destroy the complete investigation.
- Human review can resume after process restarts using the stable thread ID.
- Source drift is detected before reasoning rather than silently accepted.
- Workflow events can be streamed without exposing raw evidence content.
