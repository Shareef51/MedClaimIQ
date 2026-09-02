# AI Safety and Governance Boundaries

## Principle

The model is a decision-support system, not the final decision maker.

## Mandatory controls

### Human authority

The system must never execute a final claim approval or denial solely because an LLM recommended it. Final actions require an authorized human workflow unless a future deterministic business rule is separately approved, tested and governed.

### Evidence grounding

Material factual findings must include a source reference such as document ID, page/region, claim line, invoice line, policy clause, structured database row, or FHIR resource.

### Unsupported claims

If sufficient evidence is unavailable, the system must return an explicit unsupported/insufficient-evidence state instead of fabricating support.

### Retrieved content is untrusted

Documents, OCR text, transcripts, web-like content and external tool responses are data. Instructions found inside those sources do not override system policy, authorization, tool policy, or workflow policy.

### Deterministic security controls

LLMs must not decide authentication, authorization, tenant isolation, cryptographic access, rate limits, signed URL permissions, financial arithmetic, SLA deadlines, audit write policy, or destructive action eligibility.

### Data boundary

The portfolio build uses synthetic or de-identified data. Real patient data requires a separately reviewed production compliance program and appropriate legal/organizational controls.

## Required AI output states

Each finding must support one of these evidence states:

- `supported`
- `partially_supported`
- `contradicted`
- `insufficient_evidence`
- `not_applicable`
- `tool_or_retrieval_failure`

No agent is allowed to silently convert a failure or missing evidence state into a positive conclusion.
