# SLA, Timer, Deadline and Escalation Engine

MedClaimIQ persists deadlines rather than relying on process-local sleeps. Each timer is bound to a tenant, claim, versioned SLA policy, IANA timezone, clock mode, absolute UTC due time, warning schedule and next durable action.

## Safety and compliance boundary

The sample policy values are synthetic configuration examples. They are not legal, payer-contract, regulatory or appeal-deadline advice. Production tenants must configure and validate their own contractual/regulatory rules.

SLA automation may create warnings, breach events and human-review queue entries. It does not approve or deny a claim. External notifications remain behind the existing MCP human-approval gate.

## Business calendar

The calculator uses Python `zoneinfo` with tenant IANA timezones. Working weekdays and business start/end times come from the policy; holiday dates are tenant-persisted. Timestamps are converted back to UTC before storage. `elapsed` clock rules remain absolute elapsed time and do not skip weekends/holidays.

## Durable timer lifecycle

`scheduled -> warning(s) -> completed | breached | cancelled`

The timer worker queries `next_action_at` and does not depend on in-memory sleep state. After downtime, a recovery pass selects persisted overdue timers and emits any missed warnings before evaluating the breach. Worker failures are hash-audited with bounded exponential retry.

## Event-driven scheduling

Source events are converted to idempotent timer commands using `event_id + timer_type`. Examples include claim submission, missing-evidence requests, hospital/provider verification, reviewer action and appeal-ready events. Completion events close the relevant active timer.

Every timer transition also emits a metadata-only event to `medclaimiq.sla.events.v1` through the transactional realtime outbox. The partition key remains `claim_id`.

## Human escalation and MCP notifications

A breach creates one claim-scoped review-queue entry per timer/escalation level. Appeal deadline breaches are critical; other timer breaches are high priority by default.

The SLA engine can request `notification.claim_update` via the MCP gateway. Because that tool is high-risk/external, the request produces a persisted human approval rather than sending automatically. The action input is deterministic and non-PHI-oriented for the demo review queue.

## Realtime countdown

The countdown API returns `server_time`, UTC `due_at`, seconds remaining, percent elapsed and warning level. A frontend can tick locally between server updates while SLA warning/breach events arrive through the existing claim SSE stream.
