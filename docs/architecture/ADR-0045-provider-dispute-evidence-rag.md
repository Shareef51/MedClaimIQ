# ADR-0045 — Provider Dispute Evidence Re-Ingestion, Contract/Policy RAG and Decision Support

## Decision
Release 45 is a decision-support layer over Release 44 provider disputes. Provider evidence must cross the existing accepted-evidence/quarantine boundary before dispute-specific re-ingestion. The dispute snapshot locks provider evidence versions, the Release 44 recovery evidence-pack hash, and the exact effective provider-agreement/reimbursement-policy versions.

## Retrieval and comparison
Document, image, audio/video extraction units and trusted FHIR snapshots are normalized into a dispute-scoped retrieval namespace. Retrieval is filtered to the provider dispute and effective contract/policy versions, then persists citation-bearing RAG items. Deterministic comparison records distinguish added, changed, contradictory, corroborating and unchanged facts. Payment-policy contradictions always require human interpretation.

## Human authority
The recommendation agent has `adjudication_authority=none` and terminates at a durable `independent_human_dispute_review` checkpoint. The Release 45 service intentionally has no dependency on Release 44 `resolve_dispute`, journal posting, payment authorization, collection, or fund movement. Final dispute resolution stays in the Release 44 independent human finance-approver path.

## Provider responses
Human finance investigators may request missing evidence. A provider related to the recovery case may submit a response and evidence references. Satisfying an evidence request does not resolve the dispute; it only returns the case to the independent human review queue.
