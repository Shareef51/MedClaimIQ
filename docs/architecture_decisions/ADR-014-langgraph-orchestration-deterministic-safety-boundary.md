# ADR: LangGraph coordinates reasoning; deterministic services retain authority

## Status
Accepted.

## Decision
Use LangGraph for durable, stateful, parallel specialist-agent reasoning with PostgreSQL checkpoints and interrupt/resume. Bind each workflow to one immutable evidence pack and claim scope.

Do not expose tenant authorization, direct claim lifecycle mutation, final claim approval/denial, unrestricted SQL/FHIR access, or authoritative evidence-graph mutation as agent capabilities.

## Rationale
Agent reasoning is probabilistic. Tenant isolation, authorization, final claim actions, evidence identity, lifecycle transitions, idempotency, and auditability require deterministic enforcement. Keeping those controls outside the graph prevents model output from becoming an authorization or adjudication mechanism.

## Consequences
- agents return findings/recommendations, not final claim outcomes;
- human review interrupts are durable and resumable;
- agent executions can be replayed against a stable evidence-pack snapshot;
- a process restart does not require restarting the complete claim investigation;
- checkpoint compromise risk is reduced through strict serialization/deserialization controls;
- orchestration data stays tenant isolated through application scope plus forced PostgreSQL RLS.
