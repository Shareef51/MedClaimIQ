# ADR — Durable SLA timers and human escalation

## Decision

Persist SLA policies, holidays, timers, timer events, worker failures and escalation queue entries in PostgreSQL with tenant RLS. Compute tenant-local business time using IANA timezones but persist UTC deadlines. Drive timer creation/completion from idempotent domain events and recover due timers from persisted `next_action_at` state.

## Consequences

- Worker restarts do not lose deadlines.
- SLA policy changes are versioned; an existing timer retains the version that scheduled it.
- Broker availability is not the source of truth for deadlines.
- Warning/breach history is append-only and auditable.
- Escalation can route work to humans automatically, but cannot make a final claim decision.
- MCP notification side effects remain approval-gated.
- Tenant legal/contractual deadlines remain configuration rather than hard-coded product claims.
