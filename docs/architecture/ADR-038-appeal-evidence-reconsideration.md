# ADR-038 — Appeal Evidence Re-Ingestion and Independent Reconsideration

## Governance invariant

The original human decision and its evidence snapshot are immutable. Supplemental appeal evidence creates a separate versioned evidence snapshot and reconsideration lineage. LLMs, LangGraph nodes, RAG retrieval, MCP tools, ingestion workers, and automated workflows have **no authority** to affirm, modify, overturn, approve, deny, or financially adjudicate a claim. Only the independently assigned authorized human appeal reviewer may resolve the appeal through the existing governed post-decision resolution service.

## Runtime flow

1. A patient/provider appeal links supplemental evidence through the existing secure evidence boundary.
2. ADR-038 registers a pending appeal re-ingestion record without mutating the original decision.
3. Artifact readiness, file integrity, evidence version and malware/quarantine status are verified.
4. Document, image, audio, video and FHIR evidence is re-ingested into version-bound chunks/citations. Existing successful extraction units are reused when available; imported evidence can use a metadata-bound fallback while preserving its content SHA-256.
5. A locked appeal evidence snapshot binds original sources, supplemental sources, versions, modalities and the original decision evidence hash.
6. Structured original-vs-new comparison produces corroborating, changed and contradictory fact records with source citations.
7. Appeal-scoped hybrid dense + lexical retrieval produces a persisted citation pack. Retrieval cannot operate outside the appeal snapshot.
8. A recommendation-only reconsideration agent produces non-binding findings and persists a durable LangGraph human checkpoint.
9. The independent reviewer can annotate evidence/findings, request missing evidence, resume checkpoints or escalate to second-level human review.
10. The separate governed human resolution path (see `POST_DECISION_COMMUNICATIONS_APPEALS.md`) remains the only mechanism that can affirm, modify or overturn the controlling claim outcome.

## Traceability

`original evidence → locked original human decision → appeal → supplemental evidence/version → validated re-ingestion → immutable appeal snapshot → comparisons → RAG citations → recommendation-only agent → reviewer annotations/checkpoint/escalation → independent human appeal resolution`

Every persisted stage is tenant scoped; ADR-038 tables use PostgreSQL RLS. Locked snapshots and AI/RAG/reviewer evidence records are protected against payload rewriting by database triggers.

## Operational hardening

Reviewer mutations are idempotent by tenant and idempotency key, and retrying a recommendation run, missing-evidence request, or second-level escalation cannot duplicate the governed record. Original evidence chunks retain the accepted evidence version (separate from extraction-pipeline version), while supplemental chunks bind evidence version, extraction locator, content hash, embedding model/dimensions, and index version. Lexical ranking uses corpus-aware BM25 over the locked appeal snapshot and is fused with dense similarity when the production cached embedder is available. The reviewer UI consumes tenant/claim-scoped SSE events and refreshes the workbench as each appeal-reconsideration stage advances.
