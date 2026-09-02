# Regulatory Examination, Inquiry Response & Supervisory Evidence Management

This architecture extends the certified recovery-reporting chain into post-submission regulator interaction without weakening human control.

## Provenance chain

`certified ADR-049 filing → ADR-050 human release/transmission/ACK → ADR-051 supervisory certification → regulator inquiry → document requests → immutable evidence pack → cited financial/accounting retrieval → optional AI-assisted response draft → human maker → different human checker → secure correspondence reference → findings/remediation commitments → follow-up → human examination closure`.

## Evidence model

Each examination case is bound to an ADR-051 reconciliation case that already points to the exact certified package, human release, transmission and cryptographically verified acknowledgment. Evidence packs are immutable versions with source-watermark and payload SHA-256 values. Regulator-requested evidence is added only as explicit references; underlying ledgers, financial authorization, settlements and accounting periods are read-only.

## AI boundary

The optional OpenAI Responses structured client is disabled by default. When enabled it may synthesize a response draft from retrieved citations. The resulting record remains `draft`, persists `authority=none`, and cannot be delivered until a different authorized human checker approves it. Deterministic fallback keeps the workflow functional without a model/API key.

## Closure controls

Examination closure fails closed if any regulator document request remains open, any material finding remains unresolved, any remediation commitment remains open, or no independently approved response has been securely delivered. Background workers only age cases and raise derived supervisory escalations.

## Secure correspondence adapter

Approved responses are handed to a `RegulatoryCorrespondenceAdapter`. The portfolio uses `SandboxSecureRegulatoryCorrespondenceAdapter`, which performs no network call and returns deterministic delivery provenance. A real deployment substitutes a regulator-approved portal, SFTP, encrypted-email or secure-API adapter; adapters receive only already human-approved response content and cannot approve responses or mutate financial/accounting state.
