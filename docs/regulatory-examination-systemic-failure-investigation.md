# Regulatory Examination Systemic Failure Investigation

This capability governs repeated systemic remediation failure after multi-cycle recurrence has been identified.

## Runtime flow

`multi-cycle recurrence -> evidence reconstruction -> prior-assumption validation -> root-cause reassessment -> failed-control redesign analysis -> cross-entity causal mapping -> renewed strategy candidate -> independent human challenge -> executive human reauthorization`

## Governance boundary

AI, RAG, agents, MCP tools and workers can retrieve, correlate, score, compare, draft and recommend only. They cannot authorize renewed remediation, approve an intervention program, accept residual systemic risk, certify controls, represent regulator intent, mutate accounting records or move money.

## Evidence and immutability

Investigation cases, independent challenges, conclusions and reauthorization decisions are versioned with SHA-256 hashes. Historical program closure and recurrence evidence is referenced rather than overwritten.

## Reauthorization gates

Authorization requires reconstructed evidence, human-confirmed root cause, validated cross-entity scope, completed independent challenge, regulator follow-up impact assessment and a documented renewed strategy. The API refuses an `authorize` decision when any gate is incomplete.

## Operations

A monitoring-only worker emits supervisory alerts for invalid prior assumptions, persistent root causes, enterprise control-redesign failure and regulator-follow-up impact. Alerts never execute governance decisions.
