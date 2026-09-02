# ADR-048 — Recovery Settlement Reconciliation Intelligence & Closeout Reporting

## Decision
Release 48 is a read-only intelligence projection over governed Release 47 recovery settlement and Release 41 accounting records. It may persist only immutable derived analytics/provenance records. It cannot mutate recovery balances, evidence verification, ledger journals, payment instructions, completion certificates, accounting periods, bank transactions, collections, or funds.

## Derived records
- Versioned provider recovery balance statements bound to source watermarks.
- Portfolio/provider reconciliation analytics and aging observations.
- Explainable settlement exception investigation observations.
- Accounting-period closeout report manifests and regulatory/audit packages.
- Human-released provider portal statement delivery provenance.
- Settlement/ledger-cited RAG/copilot runs with authority `none`.

## Provider statements
Statements are generated from exact Release 47 cases, verified evidence, ledger correlations and closeout certificates. Each version is immutable. Delivery is a separate portal-publication record requiring an authorized human finance analyst/approver; publication cannot change any balance.

## RAG and model assistance
Retrieval is restricted to settlement/evidence/correlation/certificate records and requires citation IDs/hashes. Optional model synthesis uses the existing OpenAI structured-response client and must return only retrieved citation IDs. Invalid model citation sets fall back to deterministic synthesis.

## Authority
AI, LangGraph, RAG, MCP and workers may analyze, rank, explain and recommend only. They may not alter balances, post journals, authorize payment, modify closeout certificates, create bank transactions, collect funds, or move money.
