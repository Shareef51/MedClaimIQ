# Performance, Scalability and Resilience Engineering

MedClaimIQ treats performance and resilience as release evidence, not demo-time anecdotes. The checked-in policy defines measurable latency/error/throughput budgets and regression budgets. Production numbers remain environment-specific and must be demonstrated against the deployed staging/performance environment using synthetic/de-identified claims.

## Load layers

- k6: high-concurrency reviewer queue, RAG/MCP reads and SSE connection pressure.
- Locust: stateful reviewer and patient/provider journeys.
- Kafka backlog model/live broker tests: backlog drain, worker saturation and recovery.
- Datastore probes: PostgreSQL, Redis and Qdrant read latency.
- Kubernetes autoscaling checks: HPA and optional KEDA lag scaling.

## Failure model

| Dependency | Expected safe degradation |
|---|---|
| OpenAI/model provider | bounded retry, then human review; never fabricate a decision |
| Redis | cacheless/degraded operation only where correctness does not depend on cache |
| Qdrant | structured/authoritative evidence fallback or human review; vector search is not the system of record |
| Kafka/Redpanda | business transaction commits keep transactional outbox rows for later publication |
| PostgreSQL | request fails with no unsafe partial business write |
| External MCP tool | circuit breaker opens and fast-fails; approval/authorization is never bypassed |

## Chaos rules

Chaos Mesh manifests are staging-first. They are not installed with the normal production chart. Production execution requires explicit approval, a bounded blast radius and abort criteria. Any loss of tenant isolation, authorization, evidence integrity or the human-final-decision boundary is a critical failure and blocks release.

## Regression gate

A candidate blocks when a hard budget fails, p95 latency regresses beyond 10%, throughput drops beyond 10%, error rate increases beyond the allowed absolute budget, or any critical resilience experiment fails. Baseline changes must be deliberate; do not weaken a threshold only to make CI green.

## Capacity planning

`generate_capacity_model.py` produces planning estimates with explicit headroom and assumptions. These estimates are not cloud guarantees. Before production sizing, run saturation tests in an environment whose node types, managed databases, vector store, Kafka service and provider quotas match production.
