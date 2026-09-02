# Production Financial Ledger, ERA/EFT Reconciliation & Accounting Close

Release 41 extends the human-authorized Release 40 financial instruction into payer accounting. It does **not** turn MedClaimIQ into a bank or autonomous payment engine.

## Trust boundary

The source of financial truth is the latest immutable, human-authorized Release 40 payment instruction. ERA and EFT records are external settlement/remittance evidence used for correlation; they cannot create or alter claim adjudication or authorize funds. OpenAI/LLMs, LangGraph, RAG, MCP tools, workers, and provider callbacks have no authority to authorize payment, approve a recoupment, or close an accounting period.

## Double-entry ledger

Every posted journal must have non-zero, equal debits and credits. Journals are chained with `previous_journal_sha256` and `journal_sha256`; database triggers reject update/delete of posted journal headers. Settlement uses `DR claims_payable / CR cash_clearing`. Returned payments reverse that treatment. Approved adjustments and recoupments use explicit accounts and retain the human approver provenance.

## ERA/EFT correlation

One payment intent may correlate to multiple ERA and multiple EFT records. Reconciliation sums each side independently, checks currency and payment/bank/trace references, and produces `open`, `partial`, `reconciled`, `exception`, or `returned`. A settlement journal is posted only when the ERA total, EFT total, expected authorized amount, currency, and reference evidence reconcile.

## Adjustments and recoupments

A finance operator/analyst may prepare an adjustment or recoupment request. A distinct `finance_approver` must approve it. The same user cannot request and approve. Approval posts accounting entries only; it does not execute collection or movement of funds.

## Provider remittance and aging

Provider remittance status links the payment intent to the latest ERA/EFT references and reconciled/returned state. The aging queue buckets unreconciled items into `0-2d`, `3-7d`, `8-30d`, and `31+d`, with exceptions elevated in priority. The background worker may refresh age/priority metadata only.

## Accounting period close

Only an active `accounting_controller` may close a period. Close is blocked while the period contains open/partial/exception reconciliation or pending adjustments. A balanced period is sealed with a close summary and SHA-256 binding to its journal hashes. Closed periods are immutable at the database boundary.

## Traceability

The trace graph preserves: `human controlling decision → human financial authorization packet → staged financial instruction → ERA/EFT evidence → reconciliation → immutable double-entry journal → accounting period close`.
