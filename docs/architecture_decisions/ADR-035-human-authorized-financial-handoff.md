# ADR-035 — Human-authorized financial handoff after controlling adjudication

**Decision:** Financial operations consume the latest immutable human decision-history version and create a separate cryptographically bound financial authorization packet. Medical adjudication authority and financial authorization authority are intentionally separated.

**Why:** An AI-assisted claims platform must not allow recommendations, orchestration, retries, MCP tools, or transport workers to become an implicit payment authorization path. Separating the decision hash from a distinct finance authorization packet creates an auditable segregation-of-duties boundary.

**Consequences:** A changed/superseded appeal decision invalidates a stale financial packet. Fraud/payment holds fail closed. Positive payment intents require a locked packet authorized by a different `finance_approver`. Remittance can exist without a payment intent. External adapters stage instructions only; actual treasury/bank execution remains downstream under separate payer controls.
