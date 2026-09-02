# Evidence-Bound Provider Dispute Resolution and Recovery Amendment

This component turns the immutable provider-dispute analysis package into a governed human resolution. The Release 45 snapshot, exact effective provider agreement/reimbursement policy versions, RAG citations, changed facts, and material policy conflicts are bound to a versioned decision packet. A finance approver must validate and lock the packet; material disputes or material target changes require a different finance approver before closure.

## Authority boundary

LLMs, RAG, LangGraph, MCP, background workers, providers, and transport systems have no dispute-adjudication, accounting-posting, payment-authorization, collection, or fund-movement authority. The former direct recovery-service dispute resolver is retired. Final resolution exists only through the locked packet workflow.

## Recovery supersession

The original recovery position is retained as an immutable version. A final human resolution appends a new recovery-position version linked by the previous payload hash. Reductions/withdrawals create a `pending_human_finance_action` reversal/reconciliation referral; this service never posts the corresponding journal or changes payment authorization.

## Final closure

A recovery investigator with an active exclusive lease records verification of the downstream accounting/reconciliation outcome. Only after that evidence is present can the existing governed recovery closure complete the case. This preserves: provider evidence → contract/policy → human resolution → amended recovery position → accounting/reconciliation verification → final recovery closure.
