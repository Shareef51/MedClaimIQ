# ADR — Immutable Original Adjudication with Versioned Human Reconsideration

## Status
Accepted

## Context
A closed medical claim may require a decision notice, delivery retries, an appeal, supplemental evidence, and a later reconsideration. Rewriting the original adjudication would destroy auditability and make it difficult to prove what evidence and human judgment controlled at each point in time.

## Decision
1. Release 35 adjudication packets and human decision rows remain immutable source records.
2. A deterministic notice draft is generated from the locked decision/evidence hashes; an authorized human must release it.
3. Appeals reference the original released notice and original decision instead of editing them.
4. Supplemental evidence is linked by evidence ID/version/SHA after the normal secure ingestion pipeline completes.
5. Appeal reviewers must be independent of original adjudication reviewers.
6. Reconsideration creates an append-only `appeal_resolutions` record and a hash-chained `decision_history_versions` entry.
7. Delivery retries and DLQ records cannot alter adjudication state.
8. AI/agents/RAG/MCP may assist with evidence organization and drafting but can never release, affirm, modify, overturn, approve, deny, or financially execute a claim outcome.

## Consequences
This adds explicit version/history and communication records, but preserves evidentiary and legal traceability. Consumers that need the current controlling post-decision result should use the latest decision-history version, not overwrite the original Release 35 row.
