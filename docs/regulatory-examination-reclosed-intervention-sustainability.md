# Regulatory Examination Reclosed Intervention Sustainability

This capability provides post-reclosure enterprise surveillance for previously reclosed intervention programs. It measures control-health decay, detects recurrence across examination cycles, compares current evidence against prior reclosure evidence and residual-risk acceptance, correlates regulator follow-up themes, propagates recurrence across in-scope entities, and creates immutable supervisory escalation/investigation records.

## Authority boundary
AI, agents, RAG, MCP tools and workers may retrieve, compare, score, monitor and recommend only. They cannot reopen/reclose an intervention program, accept residual systemic risk, certify effectiveness, represent regulator intent, modify accounting records, authorize payments, collect funds or move money. Repeated systemic failure requires human executive and internal-audit review.

## Traceability
`reclosed intervention -> surveillance -> multi-cycle recurrence -> enterprise escalation -> human investigation -> renewed governance action`

## Supervisory controls
- Tenant-scoped records and APIs.
- Immutable SHA-256 version hashes for observations, escalations, investigations and challenge decisions.
- Multi-cycle recurrence score with explicit evidence inputs.
- Control-health threshold and material-decay alerts.
- Cross-entity propagation calculation.
- Documented regulator follow-up correlation without inferring regulator intent.
- High/critical escalation automatically requires executive and internal-audit review, but never performs the review automatically.
- Monitoring worker emits alerts only and has no approval/reopening authority.
