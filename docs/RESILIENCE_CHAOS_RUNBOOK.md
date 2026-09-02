# Resilience and Chaos Runbook

1. Use synthetic/de-identified tenant data.
2. Confirm normal API health, claim authorization, event backlog, database health and SLO state.
3. Obtain approval for any experiment outside an isolated staging namespace.
4. Apply exactly one bounded failure mode at a time initially.
5. Observe API error rate, p95/p99 latency, OpenTelemetry traces, Kafka lag, outbox depth, retries/DLQ, database state and human-review escalations.
6. Abort immediately if tenant isolation, authorization, claim finalization safety or evidence integrity is violated.
7. Remove/expire the fault and verify steady state recovery.
8. Verify no business events were lost: drain outboxes, inspect DLQ/replay state and validate affected claims.
9. Store a hashed experiment report and classify the result as passed/failed/aborted.
10. Convert every failed invariant into a regression test before rerunning the experiment.

Never describe a successful synthetic experiment as proof of contractual availability. Availability, RTO and RPO must be demonstrated continuously in the actual deployment environment.
