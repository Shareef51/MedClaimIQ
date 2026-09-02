# ADR-049 — Recovery Portfolio Control Assurance, Regulatory Submission Governance & Audit Certification

## Decision

Release 49 introduces a governed control-assurance boundary above the Release 47 financial closeout and Release 48 read-only reporting layers. It never mutates settlement balances, completion certificates, accounting journals, payment instructions, bank transactions, collections, or fund movement.

A regulatory reporting period references one or more accounting periods. Deterministic validations bind the reporting package to closed accounting periods, certified recovery completion certificates, exact recovery-to-ledger tie-outs, posted/balanced journals, absence of open material settlement exceptions, complete latest provider balance statements and provider deliveries, and Release 48 closeout reports. Active claim legal holds are included in the immutable retention manifest; destructive purge is never automatic.

## Maker-checker certification

A human maker prepares and hash-locks a package version. A different authorized human accounting/audit checker must certify that exact locked manifest and source watermark. Material control blockers fail closed. Certification is append-only and hash-chained across correction/amendment versions.

## Regulatory submission boundary

MedClaimIQ does not autonomously submit regulatory packages. An authorized human auditor/tenant administrator may stage a maker-checker-certified package and record the receipt returned by the external regulatory submission channel. This records provenance only; it is not an external submission bot and carries no financial authority.

## Corrections and amendments

A submitted package is never rewritten. Corrections create a new package version that references the submitted predecessor and records an amendment rationale. The new version repeats hash lock, maker-checker certification, staging, and receipt capture.

## AI and worker authority

AI/RAG/LangGraph/MCP may prepare, retrieve, summarize, sample, and flag control issues. The Release 49 worker may refresh deterministic attestations. None may certify, stage a submission as a human authority, record a human receipt, post accounting, authorize payment, collect funds, or move money.
