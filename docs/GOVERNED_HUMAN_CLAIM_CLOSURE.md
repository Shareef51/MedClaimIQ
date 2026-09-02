# Production Multimodal Human Decision Support, Review Resolution & Governed Claim Closure

## Purpose

This capability converts the multimodal investigation workbench into a governed human adjudication workflow without allowing any LLM, LangGraph node, RAG result, MCP tool, background worker, or automation to independently approve, deny, partially approve, financially settle, or close a medical claim.

The AI system remains decision support. The final claim decision is persisted only after an authenticated claims reviewer authors a decision packet under an active exclusive review lease and the deterministic closure service passes all required validation gates.

## Human decision packet

Each packet binds:

- the proposed human decision and mandatory human rationale;
- one or more standardized reason codes;
- immutable evidence identifiers, evidence versions, and SHA-256 hashes;
- selected multimodal agent findings;
- reviewer annotations;
- cross-modal inconsistency references;
- durable human-checkpoint references;
- the advisory AI recommendation and any human disagreement reason;
- partial-approval amounts and optional claim-line outcomes;
- the expected claim status version;
- a monotonic decision-packet version.

A packet may be revised only by creating the next version. Once validated, its canonical payload is hashed into `locked_payload_sha256`. A locked version cannot be silently edited. If an independent reviewer requests changes, the primary reviewer creates a new packet version.

## Evidence-completeness and closure validation

For approve, deny, and partial-approve outcomes, closure fails closed when any of the following conditions are detected:

- decision evidence is missing, no longer ready, has a changed evidence version, or has a changed content hash;
- a material/high/critical GraphRAG contradiction remains open;
- a material/high/critical multimodal inconsistency remains unresolved by a human `resolution` annotation;
- a required modality is missing or a multimodal specialist investigation reports a blocking modality gap;
- the latest RAG guardrail run still reports unresolved material contradictions;
- a partial approval does not contain a valid approved/denied amount split;
- required reason codes or human rationale are missing;
- the human decision differs from an advisory AI recommendation without an explicit human disagreement reason.

`request_information` and `escalate` remain allowed when evidence blockers exist because they are non-financial human outcomes intended to obtain more evidence or route the case for further human review.

## AI-vs-human disagreement

The decision-support recommendation is captured for provenance but is never authoritative. When the human reviewer selects a materially different outcome, the packet records:

- the AI recommendation;
- `ai_disagreement=true`;
- a mandatory human disagreement rationale;
- the primary human reviewer identity;
- the optional independent reviewer identity when dual-control applies.

This enables disagreement-rate evaluation and model quality analysis without allowing the model to veto or execute a human decision.

## Partial approval

`partial_approve` supports an approved amount, a derived denied amount, and optional per-claim-line outcomes. The service validates that the approved amount is greater than zero and less than the claim total and that any referenced claim line belongs to the reviewed claim.

Partial approval always requires dual control. The implementation records adjudication metadata only; it intentionally performs no payment, settlement, transfer, or financial execution.

## Escalation routing

An escalation packet requires an explicit human-selected escalation queue. Escalation preserves the claim in human review, records a persisted human escalation decision, produces real-time review events, and queues post-decision notification intents for payer operations / second-level review.

## Optimistic concurrency and reviewer leases

The primary reviewer must hold the existing exclusive claim review lease. The closure path validates:

1. the reviewer is an active `claims_reviewer` tenant member;
2. the review lease token belongs to that reviewer and has not expired;
3. the claim status version still matches the packet;
4. the packet version still matches the caller's expected version;
5. the locked packet SHA-256 still matches the canonical payload before second review and closure.

A stale browser, stale claim version, stale packet version, expired lease, or modified locked payload aborts the operation.

## Deterministic dual control

A distinct second claims reviewer is required when any deterministic rule is true:

- denial;
- partial approval;
- claim value is at least the configured high-value threshold (default synthetic policy: 10,000);
- human outcome differs from the AI recommendation;
- fraud/waste reason code is selected.

The second reviewer cannot be the primary reviewer. The independent review records the locked payload SHA-256, packet version, action, rationale, and reviewer identity. Approval changes the packet to `ready_to_close`; rejection/request-changes requires a new packet version.

## Governed claim closure

Only the primary authenticated human reviewer can execute closure, under the active review lease. Immediately before closure, the service re-runs evidence/conflict validation so a changed document or newly opened conflict cannot race the earlier validation.

The canonical claim-domain service then persists a `HumanReviewDecisionModel` and performs the corresponding human-authorized claim lifecycle transition. The governed packet receives the resulting decision ID.

Waiting agent checkpoints are resolved as `resolved_by_human_decision`, preserving the reviewer identity, decision action, rationale hash, and resolution timestamp. This closes durable AI workflow waits without granting the workflow any adjudication authority.

## Immutable adjudication audit chain

Every packet creation, packet validation, independent second review, and governed closure creates a tenant-scoped adjudication audit event. Events are append-only at the database layer and include:

- monotonic per-claim sequence;
- previous event SHA-256;
- current event SHA-256 calculated over previous hash, event type, actor, packet, payload, sequence, and timestamp;
- idempotency key and trace ID.

PostgreSQL RLS isolates every governance table by tenant. Database triggers reject update/delete attempts for independent second-review records and adjudication audit events.

## Post-decision notifications

Closure writes deterministic notification intents rather than directly contacting external recipients. This keeps external delivery retryable and avoids mixing final decision persistence with external side effects. Notification intent payloads are hashed and do not include payment execution instructions.

## SSE propagation

The governed closure service reuses the transactional review-event/outbox pipeline and emits events including:

- `review.decision_packet.created`;
- `review.decision_packet.validated`;
- `review.decision_packet.second_reviewed`;
- `review.claim.governed_closure`;
- `review.notifications.queued`.

Existing reviewer SSE subscriptions already consume the `review.` prefix, so packet status, second-review state, and closure state refresh in real time.

## Evidence-to-decision traceability

`GET /api/v1/claims/{claim_id}/review/governed-closure/traceability` produces an evidence graph connecting:

`evidence -> agent finding -> human annotation -> human decision packet -> persisted human decision`

Agent findings are labeled advisory-only. Evidence artifacts also connect directly to the decision packet through `bound_to_decision_snapshot` edges, proving which exact evidence hashes and versions were considered at closure.

## API surface

- `GET /api/v1/governed-closure-model`
- `GET /api/v1/claims/{claim_id}/review/governed-closure`
- `POST /api/v1/claims/{claim_id}/review/governed-closure/packets`
- `POST /api/v1/claims/{claim_id}/review/governed-closure/packets/{packet_id}/validate`
- `POST /api/v1/claims/{claim_id}/review/governed-closure/packets/{packet_id}/second-review`
- `POST /api/v1/claims/{claim_id}/review/governed-closure/packets/{packet_id}/close`
- `GET /api/v1/claims/{claim_id}/review/governed-closure/traceability`

The prior direct browser-facing adjudication endpoint is retired for final actions so the production reviewer UI cannot bypass the packet governance pipeline.

## Production boundary

This implementation is a portfolio/reference architecture using synthetic or de-identified data. A real medical claims deployment would additionally require payer-specific adjudication policy, legal/compliance validation, jurisdiction-specific notices, validated financial systems, formal segregation-of-duties policy, retention/legal-hold requirements, and certified operational controls.
