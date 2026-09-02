# LLMOps Observability and AI Operations

MedClaimIQ uses OpenTelemetry as the vendor-neutral correlation layer. Application spans and operational records contain hashes, IDs, counts, versions, latency, status, and token usage; they intentionally exclude raw prompts, retrieved evidence text, reviewer queries, raw tool inputs, access tokens, and patient demographics.

## Trace path

`FastAPI -> RAG -> FHIR -> LangGraph -> OpenAI -> MCP -> Kafka/Redpanda workers`

Trace IDs are returned in API response headers and propagated through event envelopes/Kafka headers where available. Application audit tables remain authoritative for claim/evidence decisions; the trace backend is an operational projection.

## Export backends

- Generic OTLP/HTTP collector via `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Phoenix via `PHOENIX_COLLECTOR_ENDPOINT` and project routing. The exporter sends OTLP spans only.
- LangSmith via its OpenTelemetry endpoint and project header. Raw prompts are not exported by MedClaimIQ custom spans.

External observability is disabled by default. Keys are environment/secret-manager inputs only.

## Cost accounting

Token usage is persisted in `ai_usage_ledger`. Cost is calculated only when an explicit, versioned model price exists. MedClaimIQ never invents a model price; unknown pricing yields `null` cost while token counts remain available.

## SLOs

The policy defines retrieval latency, agent error rate, MCP error rate, and budget thresholds. Breaches create immutable `ai_slo_events`. Thresholds in the repository are synthetic operational examples and must be tuned to production traffic and business objectives.
