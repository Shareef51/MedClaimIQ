# Product Scope

## Mission

MedClaimIQ reduces the manual effort required to verify a medical claim by collecting, normalizing, retrieving, cross-checking, and presenting evidence from multiple sources in one reviewer workflow.

## Core problem

A reviewer may need to reconcile a claim against invoices, EOBs, hospital records, coverage data, policy clauses, authorization records, historical claims, and uploaded supporting documents. The evidence is multimodal, distributed, versioned, and sometimes contradictory.

## Primary users

- Claims reviewer
- Senior reviewer / approver
- Provider or hospital staff
- Patient/member submitting supporting documents
- Compliance/audit user
- Tenant/system administrator

## Supported use cases

1. Ingest synthetic/de-identified claim evidence.
2. Extract structured evidence from PDFs, images, audio, video, spreadsheets, JSON and FHIR-style resources.
3. Normalize evidence into a claim-centered model.
4. Retrieve relevant evidence using structured retrieval, hybrid vector retrieval, temporal retrieval, and relationship-aware retrieval.
5. Verify claim facts against hospital/FHIR-style records and policy evidence.
6. Detect missing evidence, contradictions, duplicate patterns, authorization gaps and other review signals.
7. Produce evidence-backed AI recommendations with citations.
8. Route uncertain/high-risk cases to human review.
9. Maintain end-to-end provenance, auditability, evaluation and operational telemetry.

## Explicit non-goals

- Medical diagnosis
- Treatment recommendations
- Autonomous final claim approval or denial
- Autonomous legal determinations
- Production handling of real PHI in the portfolio/demo environment

## Definition of done for a claim review

A claim can be considered AI-reviewed only when:

- ingestion completed or remaining evidence is explicitly marked missing;
- all selected verification tasks have a terminal status;
- every material generated finding contains traceable evidence or is marked unsupported;
- retrieval/tool failures are surfaced rather than hidden;
- uncertainty is recorded;
- a human reviewer receives the recommendation, evidence, citations, risks and unresolved questions;
- the human review action is auditable.
