# LangGraph Durable Agent Orchestration

MedClaimIQ uses LangGraph as the stateful reasoning orchestrator while retaining deterministic security, tenant isolation, evidence provenance, and claim lifecycle control outside the model.

## Execution boundary

A workflow is permanently bound to one tenant, claim, immutable evidence pack, and LangGraph thread ID. Specialist agents receive an `AgentContext` and evidence-pack binding; they do not receive an unrestricted SQLAlchemy session, authorization mutator, claim lifecycle service, or final claim decision capability.

## Workflow shape

`supervisor -> dynamic specialist fan-out -> evidence fusion -> critic -> human gate`

The supervisor is deterministic. Independent specialists fan out through LangGraph `Send`; their result list is reducer-backed for fan-in. Evidence fusion and critic stages consume the combined findings. High-risk conditions interrupt at a persisted human checkpoint.

## Durable state

Production uses the LangGraph PostgreSQL checkpointer. Checkpointer setup is an application/worker startup concern, not a per-agent operation. `thread_id` remains stable across retry, process restart, interrupt, and resume. `LANGGRAPH_STRICT_MSGPACK=true` is the default to restrict checkpoint deserialization.

Raw source evidence is not copied into the orchestration checkpoint state. The workflow references the immutable evidence pack and evidence keys. This keeps checkpoint payloads smaller and reduces PHI propagation into orchestration storage.

## Human review

Guardrail blocks/escalations, unresolved material contradictions, persistent evidence insufficiency, and non-recoverable agent failures can create a durable human checkpoint. Resume requires the exact checkpoint ID and an authenticated principal with `claim:review` permission.

A workflow interrupt is not a final claim decision. Final approve/deny/partial-approve decisions continue to use the deterministic `ClaimDomainService.record_human_decision()` path and its existing human-only controls.

## Reliability

Agent attempts use bounded exponential retry. Every attempt is uniquely identified by workflow, agent, and attempt number. Agent executions, findings, and workflow events are append-only audit records; mutable workflow/checkpoint rows contain current coordination state. PostgreSQL RLS is forced on every orchestration table.

## Privacy and audit

Agent summaries and reviewer checkpoint messages/comments are represented by hashes in durable audit storage. Evidence references, confidence, risk flags, trace IDs, workflow events, and exact evidence-pack bindings provide replay/debug evidence without turning orchestration telemetry into a duplicate medical-record store.
