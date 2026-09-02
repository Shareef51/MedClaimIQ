# ADR: PHI-safe OpenTelemetry is the LLMOps correlation layer

## Decision
Use OpenTelemetry for cross-service traces and keep PostgreSQL audit/usage records authoritative for model versions, prompt hashes, retrieval runs, agent executions, tool calls, evaluation runs, token usage, cost, and SLO events.

## Privacy boundary
Raw prompts, medical evidence, user questions, patient demographics, and tool payloads are not exported. Sensitive free text is represented by SHA-256 when correlation is required.

## Backend portability
Phoenix, LangSmith, or another OTLP backend can be enabled by configuration. Product correctness and auditability cannot depend on any external observability vendor.
