# ADR: Transactional Outbox + Kafka API for Realtime Processing

## Decision

Use PostgreSQL as the transaction boundary and Redpanda/Kafka as the asynchronous event fabric. Never dual-write a business row and broker event from the request transaction. Commit an outbox record first, publish asynchronously, and make all consumers idempotent.

## Consequences

The platform is resilient to broker outages and supports replay, but event delivery is at-least-once rather than exactly-once end-to-end. Claim ordering is achieved by `claim_id` partitioning. A production relay should use a restricted service database credential permitted to read dispatchable outbox rows across tenants; application user credentials remain RLS constrained.
