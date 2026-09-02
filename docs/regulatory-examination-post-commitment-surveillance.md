# Regulatory Examination Post-Commitment Surveillance

This capability governs the period after a regulatory examination commitment has been human-certified closed. It continuously evaluates sustainability signals, correlates new examinations with previously closed commitments, identifies cross-entity recurrence, compares current evidence to prior certification, and opens evidence-bound recurrence investigations.

## Core flow

`closed commitment -> surveillance signal -> sustainability decay / recurrence match -> investigation -> independent reassessment -> authorized human reopen decision -> renewed corrective action -> revalidation`

## Authority boundary

AI, RAG, agents, MCP tools, and background workers may retrieve evidence, correlate signals, calculate decay, propose recurrence candidates, and generate supervisory alerts. They cannot reopen or close regulatory commitments, certify effectiveness, represent regulator intent, alter accounting records, approve payments, collect funds, or move money.

## Controls

- Every record is tenant-scoped.
- Surveillance observations and reopening decisions are immutable/version-hashed.
- New examination matching is explainable by control, obligation, theme, and root-cause similarity.
- Cross-entity propagation requires explicit evidence from multiple legal entities.
- Prior certification is compared against current effectiveness and scope evidence.
- Reopening requires an authorized human role.
- Independent reassessment is required after reopening.
- Workers publish monitoring events only and never mutate human authority state.

## Supervisory events

- `regulatory.post_commitment.sustainability_decay`
- `regulatory.post_commitment.examination_recurrence_candidate`
- `regulatory.post_commitment.cross_entity_recurrence`

## Audit evidence

Audit exports should include the original closure certification, surveillance observations, recurrence evidence, examination/finding matches, cross-entity propagation evidence, investigation versions, independent reassessments, reopen decisions, renewed action-plan links, and subsequent revalidation evidence.
