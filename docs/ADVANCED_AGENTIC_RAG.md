# Advanced Agentic RAG Architecture

MedClaimIQ's advanced retrieval layer is a bounded orchestration layer over the existing security-scoped hybrid RAG implementation. It improves query planning and evidence selection without moving authorization or knowledge lifecycle decisions into an LLM.

## Execution path

1. Require both persisted claim-read authorization and the internal `claim:view_ai_findings` permission, then build the authorized `RetrievalScope`.
2. Apply an agent retrieval profile that can only narrow the authorized domain set.
3. Perform deterministic query rewriting and allowlisted self-query metadata extraction.
4. Optionally request schema-constrained rewrites and a HyDE-style retrieval passage from the configured model. Model output is retrieval text only and cannot contain tenant, claim, ACL, or authorization filters.
5. Select dense, sparse, or hybrid routing adaptively.
6. Retrieve with Qdrant tenant/claim/ACL filtering before candidate return.
7. Re-check Release 30 governed knowledge eligibility against PostgreSQL.
8. Apply evidence-aware reranking, source diversification, parent hydration, and citation-window compression.
9. Enforce citation/source-version requirements.
10. Detect low-confidence, missing-domain, missing-code, and citation-coverage knowledge gaps.
11. Perform at most one bounded second retrieval pass when the agent profile allows it.
12. Return an explicit `answerable`, `partial`, or `insufficient` state. Insufficient evidence never becomes an autonomous claim decision.

## HyDE safety

HyDE output is a hypothetical retrieval document, not evidence and not a generated answer. It is never persisted as medical evidence, never cited to a reviewer, and never changes authorization metadata. Raw HyDE text is not stored in advanced retrieval telemetry; only its SHA-256 is retained.

## Self-query safety

Allowlisted metadata fields are `service_date_from`, `service_date_to`, `minimum_authority_rank`, and `source_type`. Self-query may make a search narrower. It cannot change tenant, claim, patient, ACL tags, or lower existing authority/temporal restrictions.

## Knowledge lifecycle

Qdrant remains a rebuildable projection. PostgreSQL remains authoritative for governed knowledge status. Retired, future-dated, or expired knowledge is filtered even during the asynchronous interval before vector deletion finishes.

## Evaluation

`scripts/run_advanced_rag_evaluations.py --gate` runs the deterministic advanced-RAG release suite and emits JSON/HTML evidence under `artifacts/advanced-rag/`.
