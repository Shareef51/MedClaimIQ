# Claim and Evidence Domain

## Purpose

MedClaimIQ persists a claim-centered evidence graph rather than treating uploaded documents as unstructured chat context. The relational model is the system of record used by later extraction, FHIR, Multi-RAG, relationship retrieval, agent workflows, review UI, and evaluation layers.

All portfolio fixtures are synthetic or de-identified. The demo repository is not a store for real patient data.

## Core persisted entities

- `patients` — tenant-local claim subject identity and external identifier mappings.
- `providers` — provider records linked to tenant-local business organizations.
- `policies` — versioned coverage references with effective-date windows.
- `encounters` — service encounters with provider and patient relationships.
- `claims` — claim header, lifecycle state, service window, reviewer assignment, policy and encounter references.
- `claim_lines` — line-level codes, units, service dates, provider references and monetary amounts.
- `evidence_artifacts` — immutable-content identities and mutable processing state for source/derived evidence.
- `evidence_lineage` — append-only parent/child provenance edges between evidence versions/derivatives.
- `claim_status_events` — append-only lifecycle transition history.
- `human_review_decisions` — append-only reviewer decisions with evidence snapshots.
- `audit_events` — append-only operational/governance history.

## Evidence provenance

Every evidence artifact records a SHA-256 content digest, source type, source system, source locator, object-storage key, media type, document type, byte size, evidence version and whether the source is considered authoritative.

Derived representations are not allowed to overwrite the source artifact. Instead, the child artifact is persisted independently and linked to the parent through `evidence_lineage`. This preserves the chain from a future RAG chunk, OCR extraction, normalized table, or transcript back to the source evidence.

## Lifecycle enforcement

Claim state is protected by:

1. a canonical allowed-transition graph;
2. tenant-scoped row locking on mutating transitions;
3. explicit `status_version` conflict checks;
4. tenant-scoped idempotency keys so replayed events do not duplicate transitions;
5. append-only transition events; and
6. a human-finalization boundary.

Generic workflow code cannot transition `human_review -> completed`. Only the human-decision service can perform that transition after validating an active claims reviewer, reviewer assignment, and an evidence snapshot.

## Tenant isolation

Every domain table carries `tenant_id`. Access is constrained by both explicit repository predicates and PostgreSQL Row-Level Security using transaction-local `app.current_tenant_id`. RLS is forced for the domain tables so normal application connections cannot accidentally bypass tenant predicates.

## Relational RAG / GraphRAG readiness

The relational keys provide deterministic relationships for future retrieval:

```text
patient
  └─ policy
  └─ encounter ─ provider organization
  └─ claim ─ policy
           ├─ encounter
           ├─ claim lines ─ provider
           └─ evidence artifacts
                    └─ evidence lineage
```

Future retrieval can therefore combine semantic evidence search with exact SQL/FHIR relationships and multi-hop relationship traversal without asking an LLM to invent entity joins.
