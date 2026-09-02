# Knowledge Lifecycle, RAG Content Governance and Continuous Reindexing

MedClaimIQ treats PostgreSQL governance records and document/evidence lineage as authoritative. Qdrant is a rebuildable retrieval projection and must never decide whether a document version is approved, temporally valid, active, or retired.

## Lifecycle

`source -> document -> immutable version -> review -> quality -> approval -> knowledge release -> active projection -> retirement`

A version records a content SHA-256, source locator, RAG source identity/version, temporal validity window, metadata, author, submitter, and independent approver. Draft or approved-but-unreleased versions are not considered production retrieval content.

## Source ownership and authority

Every source has an owner principal and authority rank. Quality gates require ownership, minimum authority, complete required metadata, valid temporal bounds, a cryptographic content digest, and citation coverage. The sample threshold is a product policy value, not a medical/legal authority determination.

## Releases

Knowledge is promoted as a manifest of exact `version_id + content_sha256` pairs. The manifest is SHA-256 hashed. The release requester cannot self-approve. Promotion verifies every item is approved, has a passing quality run, is currently within its temporal validity window, and is not blocked by a retrieval-drift event.

## Continuous reindexing

`knowledge_reindex_jobs` is the durable database queue. Incremental jobs compare PostgreSQL `rag_chunks.content_sha256` with the active `rag_index_records.embedding_input_sha256` for the target embedding model/dimensions/index version. Missing or mismatched projections are stale. Full and migration jobs rebuild all indexable chunks from PostgreSQL without rerunning OCR/extraction. Delete jobs remove the source version from Qdrant and deactivate PostgreSQL projection records.

This enables embedding/index migration without changing source content. The reindex worker uses the existing MedClaimIQ embedder cache, sparse encoder, Qdrant payload contract, tenant scoping, and idempotent point IDs.

## Retrieval drift

The governance service compares Recall, Precision, NDCG, and no-evidence rate with explicit regression budgets. A blocking drift event prevents a newer knowledge release from being promoted until resolved. Drift reports contain metrics/deltas and hashes, not patient queries or document text.

## Deletion propagation

Retirement does not delete authoritative audit/history. It schedules a projection delete. Destructive source retention/disposition remains governed by the Release 25 retention and approval controls.

## Operations

- `scripts/scan_knowledge_projection_drift.py` discovers stale projections and creates incremental jobs.
- `scripts/run_knowledge_reindex.py` processes persisted jobs.
- Run the scanner periodically (for example every 15 minutes) and the worker continuously or as a short-interval Kubernetes worker/CronJob.
- Failed jobs use bounded retries and hashed error evidence; operational teams inspect dead-letter status rather than weakening tenant/ACL constraints.
