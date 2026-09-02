# End-to-End Agent Execution Engine

MedClaimIQ runs specialist reasoning as a durable LangGraph workflow while keeping authorization, evidence identity, claim lifecycle transitions, and final claim decisions deterministic.

## Execution chain

```text
Immutable Evidence Pack
        |
        v
Evidence Rehydration + SHA-256 Validation
        |
        v
Deterministic Supervisor
        |
        v
Intake Agent
        |
        +---------------- parallel Send ----------------+
        |                                                |
        v                                                v
Hospital / Invoice / Eligibility / Policy / Coding / Duplicate / Fraud-Waste / Denial-Risk
        |                                                |
        +---------------- reducer fan-in ----------------+
                         |
                         v
                  Evidence Fusion
                         |
                         v
                       Critic
                         |
                         v
                 Decision Support
                         |
                         v
                Human Review Router
                         |
                         v
                Durable Human Interrupt
```

## Stable evidence semantics

A workflow stores an immutable evidence-pack ID and pack hash. Before an agent runs, the evidence snapshot provider reconstructs each source from the authoritative tenant-scoped source record and verifies the content SHA-256 recorded in the evidence pack. If the source no longer reproduces the original hash, the workflow fails closed and a new evidence pack must be created.

Cross-source vector evidence used for workflow packs is kept at the precise chunk level rather than context-compressed or parent-hydrated text, so the persisted hash can be reproduced from the authoritative RAG chunk.

## Failure isolation

Each parallel specialist branch opens an independent database transaction. A transient provider error can retry within the configured ceiling. A contract violation is non-retryable. An exhausted or failed specialist is recorded as a failed branch, but other specialists, fusion, critic, decision support, and human review can still proceed. The human reviewer sees the failed-agent audit trail rather than losing the whole investigation.

## Fan-in semantics

Parallel specialist outputs are collected by the LangGraph reducer. Evidence Fusion, Critic, Decision Support, and Human Review Router receive prior agent findings through workflow state. Findings remain advisory and must reference evidence keys from the immutable evidence snapshot.

## Durable interrupt/resume

The human gate creates one persisted review checkpoint and invokes the LangGraph interrupt primitive. Because LangGraph restarts an interrupted node from the beginning when it resumes, MedClaimIQ looks up and reuses the existing checkpoint rather than creating a duplicate checkpoint. The graph resumes using the same stable `thread_id` and PostgreSQL checkpointer.

`request_more_evidence` does not mutate the workflow's evidence pack. It leaves the workflow paused and requires a new evidence pack/workflow, preserving reproducibility.

## Streaming

Authenticated clients can tail the append-only workflow event log using Server-Sent Events:

```http
GET /api/v1/claims/{claim_id}/agent-workflows/{workflow_id}/events?after_sequence=0
```

Each SSE frame carries the event sequence, event type, actor, trace ID, timestamp, and privacy-safe event payload. Clients can reconnect with the last sequence as a cursor. Raw evidence text is not emitted in orchestration events.

## Execution API

A claims reviewer can start an already-created workflow execution with:

```http
POST /api/v1/claims/{claim_id}/agent-workflows/{workflow_id}/execute
```

The execution endpoint requires normal authenticated claim access plus the `claim:review` permission. The final medical-claim outcome is not changed by this endpoint.

## Safety boundary

The end-to-end engine cannot:

- change tenant identity or authorization scope;
- replace the bound evidence pack;
- write arbitrary SQL or graph queries;
- mutate canonical evidence relationships from model output;
- execute a final approve/deny action;
- bypass the persisted human review checkpoint.
