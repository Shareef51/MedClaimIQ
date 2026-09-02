# ADR — Governed human claim closure is a deterministic boundary outside AI orchestration

## Status
Accepted.

## Context
Multimodal agents can assemble strong evidence and identify cross-source inconsistencies, but final medical-claim adjudication is a high-impact business action. Allowing an LLM, agent graph, RAG result, MCP tool, or automated worker to directly translate a recommendation into approval/denial would collapse evidence support and business authority into the same probabilistic control plane.

## Decision
Final claim decisions use a separate deterministic governed-closure service. The service requires an authenticated human claims reviewer, an active exclusive reviewer lease, optimistic claim and packet versions, an evidence snapshot hash, mandatory rationale/reason codes, conflict/completeness gates, and optional deterministic dual control. AI outputs are accepted only as advisory provenance references.

For dual-control cases, a second active claims reviewer different from the primary reviewer must approve the locked packet SHA-256 before closure. Final closure revalidates evidence state, persists the canonical human decision, resolves waiting AI checkpoints, appends hash-chained audit events, queues notification intents, and emits SSE/outbox events.

## Consequences
The design intentionally adds reviewer friction to high-impact cases. In exchange it creates explicit segregation of duties, prevents silent packet mutation, preserves exact evidence versions, supports AI-vs-human disagreement measurement, and makes the final human authority boundary independently testable.

No component in `agents/`, `rag/`, `mcp/`, LangGraph orchestration, or background workers is permitted to invoke a final financial adjudication path independently.
