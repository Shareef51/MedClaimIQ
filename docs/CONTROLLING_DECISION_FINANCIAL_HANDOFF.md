# Controlling-Decision Financial Handoff, Remittance & Reconciliation

Release 40 starts only after MedClaimIQ has a controlling **human** adjudication in the immutable decision-history chain. The financial subsystem does not reinterpret medical evidence and does not grant any AI, RAG, LangGraph, MCP, adapter, webhook, or worker authority to approve a claim or authorize movement of funds.

## Control sequence

1. Resolve the newest controlling human decision-history version.
2. Bind the financial packet to the decision-history SHA-256 and evidence-snapshot SHA-256.
3. Deterministically reconcile claim lines and payer/member responsibility.
4. Generate EOB JSON and an X12 835-style integration mapping. The latter is not represented as X12-certified; trading-partner validation remains mandatory before a real interchange.
5. A finance operator locks the immutable packet.
6. A **different** human with `finance_approver` role authorizes the packet. Active fraud/payment holds block authorization.
7. Only then can a positive-value payment intent be staged. Denials produce remittance/EOB artifacts but no payment intent.
8. A provider adapter can stage the already-authorized instruction. The built-in sandbox adapter acknowledges the instruction and never moves funds.
9. Settlement states arrive through an HMAC-authenticated provider webhook or an authenticated finance integration path.
10. Deterministic reconciliation identifies amount/currency/status exceptions and creates SLA-backed operational work.
11. Void/reissue operations require a human request and a different human finance approver.

## Duplicate-payment prevention

The payment fingerprint binds tenant, claim, controlling decision-history version, authorized amount, currency and payee. Unique database constraints prevent multiple active intents for the same immutable packet/fingerprint, while request idempotency protects retries.

## Accounting and audit provenance

Financial actions are appended to a SHA-256 chained audit ledger. Records preserve the human adjudication hash, evidence hash, human finance authorizer, remittance hashes, payment fingerprint, adapter instruction hash, provider event ID, settlement payload hash, reconciliation exceptions and void/reissue approvals.

## Authority boundary

- Claims reviewers create the medical adjudication.
- Finance operators prepare/stage money-adjacent records but cannot authorize them.
- Finance approvers authorize the immutable financial packet and hold/void controls, with segregation of duties.
- Background workers and adapters can only transmit an already authorized instruction.
- External settlement callbacks can report state; they cannot create authorization.
- No component in this release directly executes bank settlement.
