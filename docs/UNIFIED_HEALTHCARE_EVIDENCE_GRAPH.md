# Unified Healthcare Evidence Graph

MedClaimIQ maintains a tenant-isolated, provenance-aware relationship layer that connects structured claims, FHIR records, accepted evidence, derived extraction units, policies, encounters, providers, EOBs, and claim lines.

## Design principles

1. **Deterministic construction.** LLM output cannot silently create authoritative entity identities, source mappings, or graph edges.
2. **Canonical identity is separate from source identity.** Every FHIR/resource/document version maps to a stable canonical entity.
3. **Source versions are immutable.** New external versions produce new source mappings instead of overwriting history.
4. **Temporal relationships are first-class.** Policy, coverage, encounter, claim-line, and evidence relationships can be evaluated for the service date.
5. **Contradictions are records, not overwritten values.** Conflicting evidence preserves both values, both sources, confidence, and resolution history.
6. **Vector stores are projections.** The relational graph/provenance database is authoritative; vector indexes can be rebuilt.
7. **Tenant isolation applies to all graph data.** PostgreSQL RLS is enabled and forced on every graph/normalization table.

## Canonical relationship model

```text
Patient
  ├── subject_of ──> Claim
  ├── covered_by ──> Coverage / Policy
  └── subject_of ──> Encounter

Claim
  ├── has_line ─────> ClaimLine
  ├── occurred_during -> Encounter
  ├── billed_by ─────> Provider / Organization
  ├── paid_by ───────> Payer Organization
  └── supported_by ──> Evidence / EOB / FHIR Resource

Evidence
  ├── derived_from ──> Original Evidence
  ├── represents ────> Extraction Unit
  └── supports ──────> Claim / ClaimLine
```

## Claim-line crosswalk

Cross-source claim lines are scored deterministically using normalized service code, service date, and amount. High-confidence matches are linked; medium-confidence candidates are explicitly marked `review_required`; low-confidence candidates remain unmatched.

## Contradictions

A mismatch never causes an automatic denial/approval. Material contradictions (patient, provider, amount, service code/date, coverage, prior authorization) become reviewable evidence records.

## RAG-ready metadata envelope

Every future RAG unit must carry tenant, claim, patient, canonical entity IDs, relationship types, immutable source version/hash, authority rank, evidence confidence, ACL tags, source locator, and temporal alignment. Retrieval is therefore evidence-aware and authorization-filterable before text reaches an LLM.
