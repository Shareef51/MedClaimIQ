# ADR: Human review uses lease locks plus optimistic claim versions

## Decision

Use a server-issued, hashed, time-bounded claim-review lease together with the claim's existing optimistic `status_version`. Final decisions require both controls.

## Rationale

Database assignment alone does not protect against two tabs or stale reviewer sessions. A permanent lock is unsafe after browser/network failure. A renewable lease supports recovery, while the status version protects against business-state changes that occur after the reviewer loaded the workbench.

## Consequences

The raw lock token is shown once and never persisted. Expired locks may be reacquired. Final human decision remains in the existing deterministic claim-domain service. Review notes/events/decision metadata are append-only for auditability.
