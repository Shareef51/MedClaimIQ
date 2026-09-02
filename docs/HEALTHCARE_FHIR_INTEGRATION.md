# Healthcare Canonical Data Model and FHIR Integration

MedClaimIQ treats FHIR as an external evidence source behind a version-aware gateway. The portfolio environment uses only synthetic resources.

## Boundary

The gateway supports the R4 resource families required by the claim verification workflow: Patient, Encounter, Coverage, Claim, ExplanationOfBenefit, DocumentReference, Organization, and Practitioner.

External resources are not written directly into core claim tables. MedClaimIQ first records an immutable resource snapshot containing the source connection, logical resource ID, `meta.versionId`, `meta.lastUpdated`, source URL, SHA-256 hash, raw resource, canonical projection, fetch time, and provenance.

## SMART-ready authentication

The gateway exposes a token-provider boundary. The included backend-services implementation uses a private-key JWT client assertion and short-lived OAuth access tokens. Private keys are deployment secrets and are never committed to the repository or persisted with FHIR snapshots.

## Identity reconciliation

Patient linkage is deterministic and conservative. Strong identifiers carry the most weight; birth date and name contribute secondary evidence. High-confidence candidates may be linked, ambiguous candidates are marked `review_required`, and weak candidates are rejected. Matching is auditable and never based on an LLM guess.

## Cross-verification

Claim/EOB evidence is normalized to a canonical financial-claim projection and compared field-by-field with uploaded/internal claim facts. Results are `match`, `partial_match`, `mismatch`, `not_found`, or `inconclusive` with findings and confidence. The result is decision support only.

## Reliability and security

- timeout and bounded retry for transient failures;
- client-side rate limiting;
- Bundle pagination with same-origin next-link enforcement;
- immutable version snapshots and provenance;
- tenant RLS on every persisted FHIR table;
- transactional outbox for healthcare events;
- synthetic mock FHIR server for local demos and tests;
- no FHIR response is treated as an instruction to the LLM or as autonomous claim authority.
