# Recovery settlement evidence and governed financial closeout

Release 47 extends the final human-controlled recovery position into downstream settlement verification. The platform records external provider repayment/remittance, refund/credit, and recoupment-offset evidence; it does not initiate collection or bank transactions.

## Invariants

1. A settlement case binds to the latest immutable Release 46 recovery-position payload SHA-256.
2. Provider-submitted evidence remains pending until a human finance operator/analyst validates references, amount, and currency.
3. Multiple verified installments may satisfy one target. Partial settlement remains open and aged.
4. Positive recovery closeout requires exact verified amount and exact correlation to posted ledger journals in one governed accounting period.
5. Open settlement exceptions block certification.
6. A finance operator/analyst prepares the completion certificate; a different human finance approver certifies it.
7. AI/LLM/LangGraph/RAG/MCP/workers have no collection, bank-transaction, accounting-approval, payment-authorization, or closeout authority.
8. Audit events and ledger correlations are immutable and hash-bound.

Traceability: Release 46 final resolution -> recovery position hash -> settlement evidence -> human verification -> ledger journal/period -> closeout certificate -> independent human approval.
