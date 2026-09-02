# ADR: Hybrid retrieval is evidence-scoped and fail-closed

## Decision

Use dense and sparse retrieval over the same authorized Qdrant payload, fuse candidates with Reciprocal Rank Fusion, rerank with deterministic evidence-quality signals, and return an explicit `no_evidence` state when retrieval confidence is insufficient.

## Rationale

Medical claims contain both semantic language and exact identifiers/codes. Dense-only retrieval can miss lexical identifiers; keyword-only retrieval can miss paraphrased policy or hospital evidence. Hybrid retrieval improves recall while deterministic typed planning keeps authorization and metadata filtering outside LLM control.

## Safety consequence

No fallback may remove tenant, claim, or ACL constraints. Temporal constraints explicitly supplied by the request are not silently relaxed. Raw reviewer queries are excluded from retrieval telemetry by default.
