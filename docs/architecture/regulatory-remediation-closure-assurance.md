# Regulatory Findings Remediation, Corrective Action Governance & Closure Assurance

This subsystem turns a material regulator finding into a durable corrective/preventive action (CAPA) program without granting AI or automation regulatory, accounting, payment, or fund-movement authority.

## Runtime flow

`regulator finding → versioned CAPA plan → human approval → corrective/preventive tasks → immutable implementation checkpoint → independent control retest → regulator follow-up response → independent human closure certification → examination closure`

## Governance invariants

- Material findings cannot use the lightweight direct finding-resolution path.
- The remediation maker/owner cannot approve the plan.
- Corrective/preventive task dependencies are deterministic and fail closed.
- Completed tasks require evidence references.
- Implementation evidence checkpoints are immutable and SHA-256 bound.
- Control retesting is performed by an authorized human independent from the maker/owner.
- Any failed/partial retest blocks an `effective` closure certificate.
- Live waivers/exceptions block effective final closure.
- Regulator follow-up responses use maker-checker human approval and immutable response-version hashes.
- Final closure certification must be performed by a human independent of the plan maker, owner, and plan approver.
- Financial/accounting impact analysis is read-only. Any actual journal/payment change remains in its existing governed subsystem.

## AI boundary

Optional model assistance may recommend remediation actions/control redesign. Every result is persisted with `authority=none` and cannot approve a plan, complete tasks, retest controls, waive exceptions, certify closure, alter financial/accounting records, authorize payments, collect funds, or move money.

## Persistence and provenance

Tenant-RLS tables preserve plans, CAPA tasks/dependencies, evidence checkpoints, retests, waivers, regulator follow-up versions, closure certificates and a SHA-256 chained audit log. Immutable database triggers protect evidence/retest/certification records.
