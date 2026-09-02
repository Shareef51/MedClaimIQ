# Financial Analytics, Reserve Adequacy & Payment Integrity

Release 42 is a read-only intelligence layer over the governed Release 40 financial handoff and Release 41 accounting ledger. Source-of-truth financial, accounting and adjudication records are never updated by analytics, RAG, agents, evaluation jobs or telemetry workers. The only writes added by this release are immutable derived observations: reserve snapshots, analytics snapshots, anomaly investigations and copilot-run evidence/provenance.

## Read model

The analytics service derives claim-level incurred/approved amount, net paid amount, outstanding reserve, reserve variance, paid-to-incurred ratio, leakage exposure, duplicate/overpayment indicators, ERA/EFT anomaly score, return exposure, recoupment aging and source citations. Portfolio aggregation adds provider payment patterns and accounting-period close readiness.

## Financial RAG / copilot

The copilot retrieves only structured evidence from human-authorized financial packets, ERA/EFT reconciliations, immutable ledger journals, financial exceptions and accounting-period readiness records. Each response carries source IDs/hashes. The current reference implementation uses deterministic lexical evidence fusion so the safety boundary and evaluation are reproducible; a production LLM can synthesize the same retrieved pack only behind the same citation and no-authority contract.

## Authority boundary

No OpenAI model, LangGraph node, RAG chain, MCP tool or background worker can edit ledger history, modify a reserve source of truth, authorize a payment, close an accounting period, change adjudication, or move funds. Anomaly investigations are recommendations to authorized humans and carry `adjudication_authority=none`, `accounting_authority=none` and `fund_movement_authority=none`.

## Observability and evaluation

Release 42 emits OpenTelemetry financial-intelligence measurements for anomaly score, leakage exposure, period-close readiness and copilot runs. The evaluation dataset asserts citation requirements, human-action requirements and no-authority behavior across reserve, leakage, reconciliation, provider-pattern and close-readiness scenarios.
