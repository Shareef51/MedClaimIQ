# Production End-to-End Integration and Release Candidate Hardening

This release-candidate layer validates MedClaimIQ as one production system rather than as isolated features. It exercises deterministic synthetic golden journeys across multimodal evidence ingestion, document intelligence, healthcare/FHIR normalization, Multi-RAG retrieval, LangGraph specialist orchestration, MCP tool boundaries, human review, governed claim closure, and regulatory governance.

## Blocking release gates

A candidate is not ready unless cross-domain golden journeys, API contracts, tenant isolation, durable workflow recovery, SSE/event integrity, failure-injection resilience, the full Alembic chain, security readiness, AI evaluation quality, and immutable release-engineering controls all pass. Evidence references and an immutable release manifest are mandatory.

## Safety and authority

Automated evaluators and workers may detect failures and prepare readiness reports. They cannot declare a release candidate or promote a release to production. Release-candidate declaration is a recorded human decision, while production promotion continues to use the existing protected-environment human approval and immutable-digest GitOps workflow. Human authority for final claim decisions and regulatory decisions is unchanged.

## Failure cases

The hardening suite covers worker restart, model/provider timeout, durable human-interrupt resume, duplicate delivery/idempotency, PostgreSQL/Redis/vector/object-storage/event-backbone failures, MCP dependency failure, SSE reconnect/replay, and cross-tenant access attempts across SQL, vectors, caches, object storage, events, RAG and agents.

## Traceability

`ingestion -> normalization/FHIR -> retrieval -> agents -> MCP -> human review -> governed closure -> regulatory governance -> regression evidence -> deterministic readiness -> human release-candidate decision -> existing human production promotion`
