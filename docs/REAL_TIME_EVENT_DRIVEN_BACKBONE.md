# Real-Time Event-Driven Backbone

MedClaimIQ uses PostgreSQL transactional outboxes and the Kafka API (Redpanda locally) to connect claim lifecycle, evidence ingestion, FHIR, LangGraph, and MCP execution without coupling business transactions to broker availability.

## Delivery contract

- Delivery is **at least once**. Consumers must be idempotent.
- `claim_id` is the partition key whenever a claim exists, preserving per-claim ordering within a topic/partition.
- Business commits never depend on Kafka availability. An outbox row is committed in the same transaction and later published by a `FOR UPDATE SKIP LOCKED` relay.
- The producer uses Kafka idempotence and `acks=all`; consumer receipts provide application-level deduplication.
- Retry is bounded. Exhausted/permanent failures are written to a DLQ record and can be replayed only through an authorized replay workflow.
- Event payloads carry references/metadata, not raw medical documents, prompts, or model context.

## Topics

`medclaimiq.claim.events.v1`, `medclaimiq.evidence.events.v1`, `medclaimiq.healthcare.events.v1`, `medclaimiq.agent.events.v1`, and `medclaimiq.mcp.events.v1`.

## Backpressure

Workers expose bounded in-flight concurrency. Production consumers should pause assigned Kafka partitions when the in-flight threshold is reached and resume after the local queue drains; offsets are committed only after the database transaction succeeds.

## Realtime client delivery

Authenticated claim clients use `/api/v1/claims/{claim_id}/realtime/events` (SSE) and resume with `after_sequence`. The stream contains operational metadata only and remains tenant/claim authorized.

## FHIR change events

FHIR subscription notifications are validated as untrusted external events and converted into healthcare sync work. Polling remains a fallback for FHIR servers without subscription support.
