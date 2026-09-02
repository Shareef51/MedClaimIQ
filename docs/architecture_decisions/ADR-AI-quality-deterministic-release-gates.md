# ADR: Deterministic AI quality gates before release

## Decision
MedClaimIQ uses versioned golden datasets, deterministic task metrics and explicit regression budgets as the authoritative release gate. Model-based judging may supplement qualitative analysis but cannot override a failed deterministic safety or correctness gate.

## Rationale
A production medical-claims evidence system must detect regressions independently across extraction, retrieval, citations, grounding, orchestration, tool policy and escalation. One composite subjective score can hide a safety regression. Explicit metrics are reproducible, auditable and suitable for CI.

## Consequences
Vector/model/prompt changes must pass the same datasets or a deliberately versioned replacement. Baseline changes are governance events rather than silent threshold changes. Release-gate records are immutable and tenant isolated.
