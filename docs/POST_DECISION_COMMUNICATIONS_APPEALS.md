# Post-Decision Communications, Appeals & Reconsideration

Release 36 extends governed human claim closure into a production-oriented post-decision lifecycle. The design treats the Release 35 adjudication packet and persisted human decision as immutable source records. Any reconsideration creates a new append-only resolution and a new decision-history version rather than editing or deleting the original decision.

## Human-authority boundary

AI, LangGraph, RAG, MCP tools, and automated workers may organize evidence, retrieve policy context, summarize, draft communication text, enqueue delivery, retry transport, and surface SLA work. They **cannot** release a decision notice, reopen an appeal, affirm/modify/overturn a decision, approve/deny a claim, or execute a financial settlement. Notice release and appeal resolution are explicit authenticated human-reviewer operations.

## Decision notices

Eligible Release 35 closure automatically creates a deterministic **draft** decision notice and the first decision-history version. The notice binds:

- original `packet_id` and `decision_id`;
- `locked_payload_sha256` from the governed decision packet;
- `evidence_snapshot_sha256` from the locked evidence set;
- versioned communication template metadata;
- explainable public-facing mappings for the human reason codes;
- appeal rights and configured appeal-window metadata;
- an explicit statement that the result was issued by an authorized human reviewer.

Draft creation is not issuance. A claims reviewer must release the notice. Release creates a delivery intent, correspondence-provenance record, task/SLA state, and realtime event.

## Communication delivery, retries and DLQ

`communication_delivery_attempts` is append-only. Delivery transport can retry up to the configured maximum. Successful transport marks the intent and notice delivered. Exhausted retries create an immutable `communication_dead_letters` record and retain the original notice and payload hashes for investigation/replay. Error details are represented by hashes rather than copied into audit records.

## Appeal intake

Authenticated patient/provider/hospital portal participants may submit an appeal against a human-released notice. The appeal stores the original packet/decision/notice references, grounds, statement, filing deadline, filing status, optimistic `appeal_version`, and trace metadata.

Appeals submitted after the configured window are:

- `rejected_untimely` when no late-filing reason is provided; or
- `late_pending_review` when a late-filing reason requires human consideration.

## Supplemental evidence

Supplemental evidence uses the existing secure evidence pipeline. An evidence artifact may be attached to an appeal only after it is tenant/claim scoped and reaches `ready` status. The appeal link persists the evidence ID, version, and content SHA-256. It never copies raw document content into the appeal record.

## Independent appeal review

The assigned appeal reviewer must be an active claims reviewer and must be different from the original primary and second reviewer. Assignment is append-only and records who assigned the reviewer, why, and that independence was verified.

Controlled reopening uses optimistic `appeal_version` checks. Reopening does not edit the original adjudication; it changes only the appeal workflow state to `in_review`.

## Reconsideration resolution

Only the assigned independent reviewer can resolve an in-review appeal. Supported outcomes are:

- `affirm` — preserves the original outcome;
- `modify` — records a new controlling human outcome;
- `overturn` — records a new controlling human outcome;
- `request_information` — pauses final reconsideration for additional evidence.

The resolution binds the original evidence snapshot hash, a supplemental-evidence snapshot hash, human reason codes/rationale, and a resolution payload hash. A resolution appends a new `decision_history_versions` entry chained to the prior version hash. The Release 35 human decision and decision packet remain unchanged.

## Decision history and traceability

The decision-history chain is append-only and SHA-256 chained:

`original evidence -> locked Release 35 packet -> original human decision -> released notice -> appeal -> supplemental evidence -> independent human resolution -> resolution notice`

The latest history version represents the controlling human resolution for post-decision operations without rewriting the historical adjudication record.

## Reviewer tasks, SLA and realtime

The post-decision task queue tracks notice release, notice delivery, appeal triage, appeal review, and supplemental-evidence review. Due times come from `config/post_decision_communications_policy.json`. SLA evaluation raises priority and emits metadata-only realtime events when due times are breached.

Internal reviewer SSE includes `appeal.*`, `communication.*`, and `sla.post_decision.*`. The external portal stream allows only minimized appeal/communication metadata and blocks internal reviewer, agent, RAG, MCP, fraud/risk, and reasoning details.

## Storage and audit controls

All Release 36 tables are tenant scoped with PostgreSQL RLS. Immutable triggers protect supplemental-evidence links, appeal assignments, appeal resolutions, decision-history versions, correspondence provenance, delivery attempts, and communication dead letters.
