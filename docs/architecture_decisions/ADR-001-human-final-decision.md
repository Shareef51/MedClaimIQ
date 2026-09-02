# ADR-001: Human Authority for Final Claim Decisions

## Status
Accepted

## Context

MedClaimIQ uses probabilistic models to extract, retrieve, compare and summarize claim evidence. Model outputs can be wrong, incomplete or affected by insufficient evidence.

## Decision

LLM/agent outputs are recommendations only. The AI workflow may classify the review recommendation as:

- `approve_support`
- `deny_support`
- `pending_documents`
- `needs_human_review`

These labels are review-support states, not final adjudication. An authorized human reviewer owns the final claim action.

## Consequences

- The UI must clearly distinguish AI recommendation from reviewer decision.
- The API must not expose an AI-only endpoint that finalizes a claim.
- Every recommendation requires provenance and confidence/evidence state.
- Reviewer override/reason data must be retained for audit and evaluation.
