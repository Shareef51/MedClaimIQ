# ADR — Provider-neutral post-decision delivery is downstream of human adjudication

## Status
Accepted.

## Decision
External claim communications are modeled as a separate transport/compliance bounded context. The input is an immutable, human-released `DecisionNoticeModel`; the output is transport evidence (dispatch, receipt, correspondence, reconciliation, incident and audit-export records).

Destinations are AES-GCM encrypted and represented outside the worker only by HMAC fingerprints. Templates require independent human approval and approved versions are immutable. Dispatch is idempotent and lease-based. Provider receipts require HMAC verification and are immutable. Regulatory delivery deadlines and retention/legal-hold state are persisted independently of claim decision state.

## Consequences

- Transport failures cannot roll back, rewrite or fabricate the underlying decision.
- Provider systems and workers need no claim-decision write permission.
- Operational recovery can safely replay delivery without replaying adjudication.
- External audit packages can prove what was released, rendered, dispatched and acknowledged without exposing raw destinations.
