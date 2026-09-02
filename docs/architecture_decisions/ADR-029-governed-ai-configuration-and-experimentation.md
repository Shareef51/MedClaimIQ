# ADR: Govern AI configuration as immutable snapshots with controlled experiments

## Status
Accepted.

## Decision
MedClaimIQ stores model, prompt and retrieval configuration as immutable tenant-scoped snapshots. Environment assignments point to an approved snapshot. Production promotion requires passing evaluation evidence and independent approval for high-risk AI changes. Experiment cohorts are deterministic and privacy-preserving; shadow output cannot affect user-visible claim decisions. Rollback switches pointers to previous snapshots rather than mutating history.

## Why
Editable prompts and model names in environment variables make provenance, rollback and regression analysis unreliable. Rebuilding or editing configuration in place also makes it impossible to prove which exact configuration produced an agent finding.

## Consequences
Runtime telemetry can identify a configuration snapshot/version, releases can detect drift, and experiments can compare champion/challenger cost-quality-latency using stable cohorts. The tradeoff is an additional governance workflow and the need to seed approved configuration assignments before enabling fail-closed production registry enforcement.
