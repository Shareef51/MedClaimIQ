# Advanced Hybrid Multi-RAG Retrieval

MedClaimIQ uses a security-scoped retrieval pipeline that combines semantic and lexical evidence retrieval without allowing retrieval logic to widen authorization boundaries.

## Retrieval pipeline

1. A deterministic healthcare query planner normalizes the request, detects relevant RAG domains, extracts exact medical/billing codes and explicit ISO dates, builds bounded query variants, and decomposes multi-part questions.
2. Dense OpenAI embeddings and a BM25-compatible sparse lexical encoder query the same domain-separated Qdrant collections.
3. Qdrant applies tenant, claim, ACL, entity, temporal, active-version, and minimum-source-authority filters before returning candidates.
4. Reciprocal Rank Fusion combines candidate lists across dense/sparse channels, query variants, subqueries, and RAG domains.
5. Evidence-aware reranking combines fused rank, lexical overlap, source authority, evidence confidence, exact-term matches, and temporal alignment.
6. Candidate diversification prevents a single source from monopolizing the final context.
7. Parent context can be hydrated from PostgreSQL while preserving the exact child citation that matched.
8. Contextual compression selects relevant parent sentences without changing the original citation anchor.
9. Retrieval confidence, requested-domain coverage, and source diversity produce an explicit `no_evidence` state when evidence is insufficient.
10. Append-only telemetry records retrieval decisions without persisting raw claim-review questions by default.

## Security invariants

Fallbacks can broaden retrieval strategy or inferred RAG domains, but they never relax `tenant_id`, `claim_id`, or server-derived ACL constraints. A low-confidence retrieval result is not converted into an answer; it is returned as `no_evidence` for downstream agent guardrails.

## Sparse representation

The dependency-light sparse encoder maps normalized lexical terms to stable feature IDs and stores log-scaled term-frequency values. Qdrant's sparse IDF modifier supplies corpus-aware inverse-document-frequency weighting. This path improves exact recall for CPT/HCPCS/ICD codes, invoice identifiers, provider terms, policy clauses, and other terminology that semantic retrieval can underweight.

## Qdrant collection versioning

Hybrid collections use named vectors `dense` and `sparse`. The default index version is `rag-v2-hybrid`, so environments with older dense-only `rag-v1` collections can rebuild into new collections without in-place vector-schema mutation.

## Telemetry and privacy

`rag_retrieval_runs` stores the SHA-256 and length of the query, not raw query text. Candidate telemetry captures ranking signals and safe source metadata. Both tables are tenant-RLS protected and append-only for forensic reproducibility.
