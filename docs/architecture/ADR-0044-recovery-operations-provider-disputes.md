# ADR-0044 — Recovery operations, provider disputes and outcome verification

## Decision
Release 44 observes the outcome of already-governed Release 43 remediation referrals. Recovery records are evidence/provenance records, not payment execution commands. Provider disputes are bound to immutable recovery evidence packs and resolved only by an independent human `finance_approver`.

## Controls
- Only executed governed remediation referrals can create recovery cases.
- Recovery evidence packs, outcomes, correspondence and audit events are immutable and tenant-RLS protected.
- Finance investigators use exclusive expiring leases for case mutations.
- Partial/multiple recoveries are supported as externally evidenced observations.
- Material provider disputes are escalated and cannot be resolved by the submitting provider or assigned investigator.
- Open disputes and missing remediation verification block human case closure.
- The background worker can create tracking cases only; it cannot resolve disputes, record recovery amounts, approve accounting, authorize payments, post journals, collect funds or move money.
- Traceability preserves anomaly → investigation → remediation → recovery/dispute → downstream accounting/reconciliation lineage.

## Non-authority
LLMs, LangGraph, RAG, MCP, workers and external providers may analyze or supply evidence. They cannot adjudicate provider disputes, approve accounting changes, authorize payment, collect funds or move money.
