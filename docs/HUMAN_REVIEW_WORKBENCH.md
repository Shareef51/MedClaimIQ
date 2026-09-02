# Human Review Workbench and Decision Operations

MedClaimIQ treats AI output as advisory evidence, never as the final claim decision. The human-review backend provides a prioritized queue and a claim workbench that joins authoritative claim state with evidence, FHIR verification, graph relationships, contradictions, agent findings, guardrails, MCP approvals, SLA clocks, reviewer notes, and an immutable timeline.

## Concurrency

A reviewer acquires a short-lived lease for a claim. Only a SHA-256 digest of the bearer lock token is persisted. The lock is reviewer-bound, renewable, automatically expires, and is paired with optimistic `claim.status_version` checks before a decision. This protects against stale tabs and concurrent reviewers.

## Decision boundary

Final decisions still flow through `ClaimDomainService.record_human_decision()`. The workbench cannot bypass the canonical lifecycle. A decision requires an evidence snapshot and reason codes. If the human choice differs from the latest advisory Decision-Support recommendation, a meaningful override reason is required and preserved in immutable metadata.

## Review data

The workbench exposes source identifiers/citations and operational metadata. Original evidence remains the source of truth; derived evidence retains lineage. RAG evidence packs, FHIR versions, graph contradictions and agent findings remain independently auditable.

## Queue priority

Priority is deterministic and explainable. Inputs include lifecycle state, breached/critical SLA items, grounding escalations, waiting LangGraph human checkpoints, unresolved material contradictions, and a bounded high-value-claim factor. LLMs do not set queue priority.

## Realtime

Lock, note, review-start, evidence-request and decision events are written to the append-only review action stream and transactionally projected into the existing claim realtime outbox.
